"""
Plugin: modo_jogo — gets the PC ready to play.

"Atena, modo jogo":
  1. closes heavy programs (Brave, VS Code, other browsers… see FECHAR below),
     politely first so they can save, then forcing any that refuse
  2. switches Windows to the High performance power plan
  3. silences Windows notifications and turns Night light OFF
  4. minimises every window and hides ATENA in the tray → a clean desktop
     (ATENA keeps listening: say "Atena" to call her)

"sair do modo jogo" / "Atena, sair do modo jogo" / "modo normal":
  turns notifications and Night light back on (the PC stays on High
  performance, which is how the user always keeps it).
"""

import json
import os
import subprocess
import time
from pathlib import Path

# Programs closed by "modo jogo" (process names). Edit freely.
FECHAR = [
    "brave.exe",          # Brave
    "Code.exe",           # VS Code
    "chrome.exe",         # Google Chrome
    "msedge.exe",         # Microsoft Edge
    "firefox.exe",        # Firefox
    "claude.exe",         # Claude desktop app
    "OneDrive.exe",       # OneDrive sync
    "Teams.exe", "ms-teams.exe",
    "WINWORD.EXE", "EXCEL.EXE", "POWERPNT.EXE",
]

HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"   # Windows' built-in GUID
_STATE = Path(__file__).resolve().parent.parent / "config" / "modo_jogo.json"
_NO_WINDOW = 0x08000000

PLUGIN = {
    "name": "modo_jogo",
    "description": (
        "Game mode for this PC. action='on' when the user says 'modo jogo' or "
        "'Atena, modo jogo': closes heavy programs (browsers, VS Code, Office…), "
        "the Claude app…), makes sure the High performance power plan is active, "
        "silences notifications, turns Night light off and leaves a clean desktop. "
        "action='off' when the user says 'sair do modo jogo', 'Atena, sair do modo "
        "jogo' or 'modo normal': turns notifications and Night light back on. "
        "Answer in ONE short sentence."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {"action": {"type": "STRING", "description": "on | off"}},
        "required": [],
    },
}


def _run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True,
                          creationflags=_NO_WINDOW, **kw)


def _running(names):
    out = _run(["tasklist", "/FO", "CSV", "/NH"]).stdout.lower()
    return [n for n in names if f'"{n.lower()}"' in out]


def _close_apps() -> list[str]:
    targets = _running(FECHAR)
    for n in targets:                       # polite close (lets apps save/restore)
        _run(["taskkill", "/IM", n])
    if targets:
        time.sleep(4)
        for n in _running(targets):         # whatever ignored the request
            _run(["taskkill", "/F", "/IM", n])
    return targets


def _active_scheme() -> str | None:
    out = _run(["powercfg", "/getactivescheme"]).stdout
    for tok in out.split():
        if tok.count("-") == 4 and len(tok) == 36:
            return tok
    return None


def _set_toasts(enabled: bool) -> None:
    import winreg
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\PushNotifications")
    winreg.SetValueEx(key, "ToastEnabled", 0, winreg.REG_DWORD, 1 if enabled else 0)
    winreg.CloseKey(key)


_NL_KEY = (r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount"
           r"\Current\default$windows.data.bluelightreduction.bluelightreductionstate"
           r"\windows.data.bluelightreduction.bluelightreductionstate")


def _set_night_light(enabled: bool) -> str:
    """Toggle Windows Night light. There is no public API, so this edits the
    same registry blob the Settings app writes. Returns 'on', 'off',
    'unchanged' or 'unsupported'."""
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _NL_KEY, 0,
                             winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError:
        return "unsupported"
    try:
        data, kind = winreg.QueryValueEx(key, "Data")
        data = bytearray(data)
        if len(data) < 25 or data[18] not in (0x13, 0x15):
            return "unsupported"
        is_on = data[18] == 0x15
        if is_on == enabled:
            return "unchanged"
        if enabled:
            data[18] = 0x15
            data[23:23] = b"\x10\x00"
        else:
            data[18] = 0x13
            if data[23:25] == b"\x10\x00":
                del data[23:25]
        # bump the change timestamp so Windows notices the new value
        for i in range(10, 15):
            if data[i] != 0xFF:
                data[i] += 1
                break
        winreg.SetValueEx(key, "Data", 0, kind, bytes(data))
        return "on" if enabled else "off"
    finally:
        winreg.CloseKey(key)


def _minimise_all() -> None:
    _run(["powershell", "-NoProfile", "-Command",
          "(New-Object -ComObject Shell.Application).MinimizeAll()"])


def _on(player) -> str:
    closed = _close_apps()
    perf = _run(["powercfg", "/setactive", HIGH_PERFORMANCE]).returncode == 0
    if not perf:                            # some PCs only expose the alias
        perf = _run(["powercfg", "/setactive", "SCHEME_MIN"]).returncode == 0
    try:
        _set_toasts(False)
        quiet = True
    except Exception:
        quiet = False
    try:
        night = _set_night_light(False)
    except Exception:
        night = "unsupported"
    _minimise_all()
    if player is not None and hasattr(player, "hide_to_tray"):
        try:
            player.hide_to_tray()
        except Exception:
            pass
    names = ", ".join(n.replace(".exe", "").replace(".EXE", "") for n in closed) or "nothing"
    if player:
        try:
            player.write_log(f"SYS: Modo jogo — fechados: {names}; alto desempenho: "
                             f"{'sim' if perf else 'não'}; notificações: "
                             f"{'silenciadas' if quiet else 'não alteradas'}; luz noturna: "
                             f"{'desligada' if night in ('off', 'unchanged') else 'não suportada'}")
        except Exception:
            pass
    return (f"Game mode on. Closed: {names}. High performance: {'yes' if perf else 'no'}. "
            f"Notifications silenced: {'yes' if quiet else 'no'}. "
            f"Night light off: {'yes' if night in ('off', 'unchanged') else 'could not change'}. "
            "Desktop cleared.")


def _off(player) -> str:
    # The PC always stays on High performance — only notifications come back.
    try:
        _set_toasts(True)
    except Exception as e:
        return f"Could not turn notifications back on: {e}"
    try:
        night = _set_night_light(True)
    except Exception:
        night = "unsupported"
    ok = night in ("on", "unchanged")
    if player:
        try:
            player.write_log("SYS: Modo jogo desligado — notificações e luz noturna de volta."
                             if ok else "SYS: Modo jogo desligado — notificações de volta "
                             "(não consegui religar a luz noturna).")
        except Exception:
            pass
    return ("Game mode off. Notifications and Night light are back on." if ok else
            "Game mode off. Notifications are back on, but Night light could not be changed.")


def run(parameters: dict, player=None, session_memory=None) -> str:
    if os.name != "nt":
        return "Game mode is only available on Windows."
    action = (parameters.get("action") or "on").strip().lower()
    try:
        return _off(player) if action in ("off", "desligar", "sair", "normal") else _on(player)
    except Exception as e:
        return f"Game mode failed: {e}"
