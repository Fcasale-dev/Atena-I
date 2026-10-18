"""
core/activity.py — what the user did today, for the end-of-day summary.

  * every 5 s: which program is in the foreground (Windows), counted as active
    time unless the PC has been idle (no mouse/keyboard) for 5+ minutes
  * every ATENA command (tool call), so the summary can say what she did

Everything stays on this PC, in config/uso/<date>.json. Nothing is sent
anywhere until the user asks for the summary.
"""

from __future__ import annotations

import ctypes
import json
import os
import threading
import time
from datetime import date, datetime
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "config" / "uso"
SAMPLE_S = 5
IDLE_S = 300

FRIENDLY = {
    "brave.exe": "Brave", "chrome.exe": "Chrome", "msedge.exe": "Edge",
    "firefox.exe": "Firefox", "code.exe": "VS Code", "claude.exe": "Claude",
    "steam.exe": "Steam", "steamwebhelper.exe": "Steam", "discord.exe": "Discord",
    "spotify.exe": "Spotify", "explorer.exe": "Explorador de Arquivos",
    "git-bash.exe": "Git Bash", "mintty.exe": "Git Bash", "windowsterminal.exe": "Terminal",
    "cmd.exe": "Prompt de Comando", "powershell.exe": "PowerShell",
    "winword.exe": "Word", "excel.exe": "Excel", "powerpnt.exe": "PowerPoint",
    "obs64.exe": "OBS", "vlc.exe": "VLC", "whatsapp.exe": "WhatsApp",
    "python.exe": "ATENA", "pythonw.exe": "ATENA",
    "cs2.exe": "Counter-Strike 2", "eldenring.exe": "Elden Ring",
}

_lock = threading.Lock()
_day = None
_apps: dict[str, float] = {}
_actions: list[list] = []
_first = _last = None
_started = False


def _path(d: date) -> Path:
    return DIR / f"{d.isoformat()}.json"


def _load(d: date) -> None:
    global _apps, _actions, _first, _last, _day
    try:
        data = json.loads(_path(d).read_text(encoding="utf-8"))
    except Exception:
        data = {}
    _apps = data.get("apps", {})
    _actions = data.get("actions", [])
    _first, _last = data.get("first"), data.get("last")
    _day = d


def _save() -> None:
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        _path(_day).write_text(json.dumps(
            {"apps": _apps, "actions": _actions[-300:], "first": _first, "last": _last},
            ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        print(f"[Activity] save failed: {e}")


def _idle_seconds() -> float:
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(li)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
        return (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0
    return 0.0


def _foreground_app() -> str | None:
    try:
        import psutil
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        name = psutil.Process(pid.value).name()
        low = name.lower()
        if low in FRIENDLY:
            return FRIENDLY[low]
        return name[:-4] if low.endswith(".exe") else name
    except Exception:
        return None


def _loop() -> None:
    global _first, _last
    ticks = 0
    while True:
        time.sleep(SAMPLE_S)
        try:
            today = date.today()
            with _lock:
                if _day != today:
                    if _day is not None:
                        _save()
                    _load(today)
                if _idle_seconds() < IDLE_S:
                    app = _foreground_app()
                    if app:
                        _apps[app] = _apps.get(app, 0) + SAMPLE_S
                        now = datetime.now().strftime("%H:%M")
                        _first = _first or now
                        _last = now
                ticks += 1
                if ticks % 12 == 0:            # save once a minute
                    _save()
        except Exception as e:
            print(f"[Activity] {e}")


def clear(d: date) -> None:
    """Forget a day: wipe it from memory and delete its file."""
    global _apps, _actions, _first, _last
    with _lock:
        if d == _day:
            _apps, _actions, _first, _last = {}, [], None, None
        try:
            _path(d).unlink()
        except Exception:
            pass


def _cleanup_old(keep_days: int = 2) -> None:
    """Delete day files older than `keep_days` so nothing piles up."""
    try:
        for f in DIR.glob("*.json"):
            try:
                if (date.today() - date.fromisoformat(f.stem)).days > keep_days:
                    f.unlink()
            except Exception:
                continue
    except Exception:
        pass


def start() -> None:
    global _started
    if _started or os.name != "nt":
        return
    _started = True
    _cleanup_old()
    with _lock:
        _load(date.today())
    threading.Thread(target=_loop, daemon=True, name="Activity").start()


def record_action(tool: str, args: dict | None = None) -> None:
    """Called by main for every tool ATENA runs."""
    if tool in ("resumo_dia", "recall_memory", "save_memory"):
        return
    try:
        short = ""
        if args:
            for k in ("action", "app_name", "query", "folder", "game", "target", "message",
                      "name", "path", "url", "mood"):
                if args.get(k):
                    short += f" {k}={str(args[k])[:40]}"
        with _lock:
            if _day != date.today():
                _load(date.today())
            _actions.append([datetime.now().strftime("%H:%M"), tool, short.strip()])
            _save()
    except Exception:
        pass


def summary(d: date | None = None) -> dict:
    d = d or date.today()
    with _lock:
        if d == _day:
            apps, actions, first, last = dict(_apps), list(_actions), _first, _last
        else:
            try:
                data = json.loads(_path(d).read_text(encoding="utf-8"))
            except Exception:
                data = {}
            apps, actions = data.get("apps", {}), data.get("actions", [])
            first, last = data.get("first"), data.get("last")
    return {"date": d.isoformat(), "apps": apps, "actions": actions,
            "first": first, "last": last}
