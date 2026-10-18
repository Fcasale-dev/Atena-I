"""
Plugin: status_pc — "Como está o PC?" / "Como está o computador?"

Answers with CPU temperature, GPU temperature, RAM use (and CPU/GPU load).

Temperatures on AMD Ryzen / Radeon are not exposed by Windows itself, so they
are read from LibreHardwareMonitor (free, open source), in this order:
  1. its web server  → http://localhost:8085/data.json   (Options → Remote Web Server → Run)
  2. its WMI provider → root\\LibreHardwareMonitor          (works whenever it is running)
  3. Windows' ACPI thermal zone (rough, often missing)
RAM and load always work (psutil).
"""

import os
import subprocess
import time

import psutil

from core.hw_sensors import read_sensors

PLUGIN = {
    "name": "status_pc",
    "description": (
        "Reports how the computer is doing: CPU temperature, GPU (video card) "
        "temperature, RAM usage, CPU/GPU load and how long the PC has been on. Call when the user asks 'como "
        "está o PC?', 'como está o computador?', 'temperatura do PC', 'quanto de RAM "
        "estou usando'. Use this instead of system_status. Answer in 2 short "
        "sentences in Portuguese and ALWAYS include: CPU temperature and CPU usage %, "
        "GPU temperature and GPU usage %, RAM usage and uptime. If a value is "
        "missing, say it briefly and follow the hint in the result."
    ),
    "parameters": {"type": "OBJECT", "properties": {}, "required": []},
}

def _gpu_load_windows():
    """GPU 3D-engine usage from Windows' own performance counters (works for
    AMD/NVIDIA/Intel without extra software)."""
    if os.name != "nt":
        return None
    cmd = ("$s=(Get-Counter '\\GPU Engine(*engtype_3D)\\Utilization Percentage' "
           "-ErrorAction Stop).CounterSamples | Measure-Object -Property CookedValue -Sum; "
           "[math]::Round($s.Sum,1)")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=6,
                           creationflags=0x08000000)
        v = float((r.stdout or "").strip().replace(",", "."))
        return max(0.0, min(100.0, v))
    except Exception:
        return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    ram = psutil.virtual_memory()
    cpu_load = psutil.cpu_percent(interval=0.3)
    sensors = read_sensors()
    up = time.time() - psutil.boot_time()
    up_h, up_m = int(up // 3600), int((up % 3600) // 60)

    parts = []
    ct, gt = sensors.get("cpu_temp"), sensors.get("gpu_temp")
    parts.append(f"CPU temperature: {ct:.0f} °C" if ct else "CPU temperature: unavailable")
    if gt:
        hs = sensors.get("gpu_hotspot")
        parts.append(f"GPU temperature: {gt:.0f} °C" + (f" (hot spot {hs:.0f} °C)" if hs else ""))
    else:
        parts.append("GPU temperature: unavailable")
    parts.append(f"RAM: {ram.percent:.0f}% in use ({ram.used / 1024**3:.1f} of "
                 f"{ram.total / 1024**3:.1f} GB)")
    parts.append(f"CPU usage: {cpu_load:.0f}%")
    gl = sensors.get("gpu_load")
    if gl is None:
        gl = _gpu_load_windows()
    parts.append(f"GPU usage: {float(gl):.0f}%" if gl is not None else "GPU usage: unavailable")
    parts.append(f"Computer on for: {up_h} h {up_m} min")

    text = ". ".join(parts) + "."
    if not (ct and gt):
        text += (" Hint for the user: to read AMD temperatures, open LibreHardwareMonitor "
                 "(as administrator) and leave it running in the tray.")
    if player:
        try:
            player.write_log("SYS: " + text.split(" Hint")[0])
        except Exception:
            pass
    return text
