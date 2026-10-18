"""
Plugin: desligar_pc — shut down / restart the PC by voice, with a safety window.

Say:
  "desligar PC", "desligue o PC", "desligar computador"  → shuts down in 30 s
  "reiniciar PC", "reinicia o computador"                 → restarts in 30 s
  "cancelar", "cancela o desligamento", "não desliga"     → aborts it

The 30-second countdown is the safety net: if ATENA misheard, just say
"cancelar". Windows also shows its own "you're about to be signed out" notice.
"""

import os
import platform
import subprocess

DELAY_S = 30

PLUGIN = {
    "name": "desligar_pc",
    "description": (
        "Shuts down or restarts THIS COMPUTER by voice, after a 30-second countdown "
        "that can be cancelled. Call with action='shutdown' when the user says "
        "'desligar PC', 'desligue o PC', 'desligar computador', 'desliga o computador'; "
        "action='restart' for 'reiniciar PC/computador'; action='cancel' when they say "
        "'cancelar', 'cancela o desligamento', 'não desliga'. Use this instead of "
        "computer_settings shutdown/restart. Do NOT use it for closing the assistant "
        "('encerrar Atena' → shutdown_jarvis). After calling, tell the user it will "
        "happen in 30 seconds and that they can say 'cancelar'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "shutdown | restart | cancel"},
        },
        "required": ["action"],
    },
}

_NO_WINDOW = 0x08000000


def _run(args):
    kw = {"capture_output": True, "text": True}
    if os.name == "nt":
        kw["creationflags"] = _NO_WINDOW
    return subprocess.run(args, **kw)


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "shutdown").strip().lower()
    system = platform.system()
    try:
        if action in ("cancel", "cancelar", "abort"):
            if system == "Windows":
                r = _run(["shutdown", "/a"])
                if r.returncode != 0:
                    return "There was no shutdown or restart scheduled to cancel."
            else:
                _run(["shutdown", "-c"])
            msg = "Cancelled — the computer will stay on."
        elif action in ("restart", "reiniciar", "reboot"):
            if system == "Windows":
                _run(["shutdown", "/r", "/t", str(DELAY_S)])
            else:
                _run(["shutdown", "-r", f"+{max(1, DELAY_S // 60)}"])
            msg = (f"Restarting the computer in {DELAY_S} seconds. "
                   "Say 'cancelar' to stop it.")
        else:
            if system == "Windows":
                _run(["shutdown", "/s", "/t", str(DELAY_S)])
            else:
                _run(["shutdown", "-h", f"+{max(1, DELAY_S // 60)}"])
            msg = (f"Shutting the computer down in {DELAY_S} seconds. "
                   "Say 'cancelar' to stop it.")
        if player:
            try:
                player.write_log(f"SYS: {msg}")
            except Exception:
                pass
        return msg
    except Exception as e:
        return f"Could not run the command: {e}"
