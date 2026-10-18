"""
core/hw_sensors.py — CPU / GPU temperatures (and GPU load) for AMD, Intel and
NVIDIA, shared by the status_pc plugin and the system_status tool.

Windows does not expose Ryzen / Radeon temperatures itself, so they are read
from LibreHardwareMonitor (free, open source) when it is running:
  1. its web server  → http://localhost:8085/data.json
  2. its WMI provider → root\\LibreHardwareMonitor
  3. Windows' ACPI thermal zone (rough, CPU only)
Results are cached for a few seconds so both tools can call it freely.
"""

import json
import os
import re
import subprocess
import time

_NO_WINDOW = 0x08000000


def _num(v):
    try:
        m = re.search(r"-?\d+(?:[.,]\d+)?", str(v))
        return float(m.group(0).replace(",", ".")) if m else None
    except Exception:
        return None


# ── 1. LibreHardwareMonitor web server ───────────────────────────────────────
def _from_lhm_web():
    try:
        import requests
        r = requests.get("http://localhost:8085/data.json", timeout=1.5)
        tree = r.json()
    except Exception:
        return None
    out = {}

    def walk(node, hw=""):
        text = node.get("Text", "")
        kids = node.get("Children", []) or []
        sid = (node.get("SensorId") or "").lower()
        img = (node.get("ImageURL") or "").lower()
        if "cpu" in img or re.search(r"ryzen|intel|core i\d", text, re.I):
            hw = "cpu"
        elif "ati" in img or "nvidia" in img or re.search(r"radeon|geforce|rtx|gtx|arc", text, re.I):
            hw = "gpu"
        val = node.get("Value", "")
        if "°c" in str(val).lower() and hw:
            name = text.lower()
            t = _num(val)
            if hw == "cpu" and t is not None:
                if "tctl" in name or "package" in name:
                    out["cpu_temp"] = t
                else:
                    out.setdefault("cpu_temp_any", t)
            if hw == "gpu" and t is not None:
                if name.startswith("gpu core") or name == "gpu":
                    out["gpu_temp"] = t
                elif "hot spot" in name:
                    out["gpu_hotspot"] = t
                else:
                    out.setdefault("gpu_temp_any", t)
        if "%" in str(val) and hw == "gpu" and text.lower() in ("gpu core", "d3d 3d"):
            out.setdefault("gpu_load", _num(val))
        for k in kids:
            walk(k, hw)

    walk(tree)
    out.setdefault("cpu_temp", out.pop("cpu_temp_any", None))
    out.setdefault("gpu_temp", out.pop("gpu_temp_any", None))
    return out if (out.get("cpu_temp") or out.get("gpu_temp")) else None


# ── 2. LibreHardwareMonitor WMI provider ─────────────────────────────────────
def _from_lhm_wmi():
    cmd = ("Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor "
           "-ErrorAction Stop | Select-Object Name,Value,SensorType,Identifier | "
           "ConvertTo-Json -Compress")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=6,
                           creationflags=_NO_WINDOW)
        rows = json.loads(r.stdout or "[]")
    except Exception:
        return None
    if isinstance(rows, dict):
        rows = [rows]
    out = {}
    for s in rows:
        ident = (s.get("Identifier") or "").lower()
        name = (s.get("Name") or "").lower()
        kind = (s.get("SensorType") or "").lower()
        val = s.get("Value")
        if kind == "temperature":
            if "cpu" in ident:
                if "tctl" in name or "package" in name:
                    out["cpu_temp"] = val
                else:
                    out.setdefault("_cpu", val)
            elif "gpu" in ident:
                if name == "gpu core":
                    out["gpu_temp"] = val
                elif "hot spot" in name:
                    out["gpu_hotspot"] = val
                else:
                    out.setdefault("_gpu", val)
        elif kind == "load" and "gpu" in ident and name == "gpu core":
            out["gpu_load"] = val
    out.setdefault("cpu_temp", out.pop("_cpu", None))
    out.setdefault("gpu_temp", out.pop("_gpu", None))
    out.pop("_cpu", None); out.pop("_gpu", None)
    return out if (out.get("cpu_temp") or out.get("gpu_temp")) else None


# ── 3. ACPI thermal zone (rough fallback, CPU only) ──────────────────────────
def _from_acpi():
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
             "-ErrorAction Stop | Select-Object -First 1).CurrentTemperature"],
            capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW)
        k = _num(r.stdout)
        if k:
            return {"cpu_temp": round(k / 10 - 273.15, 1)}
    except Exception:
        pass
    return None



_cache = {"t": 0.0, "v": {}}


def read_sensors(max_age: float = 5.0) -> dict:
    """{'cpu_temp', 'gpu_temp', 'gpu_hotspot', 'gpu_load'} — missing keys = unknown."""
    if os.name != "nt":
        return {}
    if time.time() - _cache["t"] < max_age:
        return dict(_cache["v"])
    v = _from_lhm_web() or _from_lhm_wmi() or _from_acpi() or {}
    v = {k: x for k, x in v.items() if x is not None}
    _cache.update(t=time.time(), v=v)
    return dict(v)
