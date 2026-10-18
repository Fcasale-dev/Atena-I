"""
Plugin: abrir_claude — opens the Claude desktop app.

Say: "abrir Claude", "abre o Claude", "abra o Claude".

Tries, in order:
  1. The usual install locations of Claude.exe
  2. A "Claude" shortcut in the Start Menu
  3. The Start-apps list (Microsoft Store / MSIX installs)
  4. The claude:// link the app registers
"""

import glob
import os
import subprocess

PLUGIN = {
    "name": "abrir_claude",
    "description": (
        "Opens the Claude desktop app (Anthropic's AI assistant) on this PC. "
        "Call when the user says 'abrir Claude', 'abre o Claude', 'abra o Claude', "
        "'open Claude'. Use this instead of open_app for Claude."
    ),
    "parameters": {"type": "OBJECT", "properties": {}, "required": []},
}

_NO_WINDOW = 0x08000000


def _candidates() -> list[str]:
    la = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    paths = [
        os.path.join(la, "AnthropicClaude", "claude.exe"),
        os.path.join(la, "Programs", "Claude", "Claude.exe"),
        os.path.join(la, "Programs", "claude", "Claude.exe"),
        os.path.join(pf, "Claude", "Claude.exe"),
    ]
    # Squirrel installs keep versioned folders: AnthropicClaude\app-x.y.z\claude.exe
    paths += sorted(glob.glob(os.path.join(la, "AnthropicClaude", "app-*", "claude.exe")),
                    reverse=True)
    return [p for p in paths if p and os.path.isfile(p)]


def _start_menu_shortcut() -> str | None:
    roots = [os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
             os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                          r"Microsoft\Windows\Start Menu\Programs")]
    for r in roots:
        for lnk in glob.glob(os.path.join(r, "**", "Claude*.lnk"), recursive=True):
            return lnk
    return None


def _store_app_id() -> str | None:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-StartApps | Where-Object { $_.Name -eq 'Claude' } | "
             "Select-Object -First 1 -ExpandProperty AppID"],
            capture_output=True, text=True, timeout=8, creationflags=_NO_WINDOW,
        )
        app_id = (out.stdout or "").strip()
        return app_id or None
    except Exception:
        return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    try:
        exe = next(iter(_candidates()), None)
        if exe:
            subprocess.Popen([exe], close_fds=True)
            how = exe
        else:
            lnk = _start_menu_shortcut()
            if lnk:
                os.startfile(lnk)
                how = lnk
            else:
                app_id = _store_app_id()
                if app_id:
                    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
                    how = f"AppsFolder\\{app_id}"
                else:
                    os.startfile("claude://")
                    how = "claude://"
        if player:
            try:
                player.write_log(f"SYS: Abrindo Claude ({how})")
            except Exception:
                pass
        return "Claude opened."
    except Exception as e:
        return (f"Could not open Claude: {e}. The Claude desktop app may not be "
                "installed on this PC.")
