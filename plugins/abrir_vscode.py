"""
Plugin: abrir_vscode — opens Visual Studio Code.

Say: "abrir VS Code", "abre o VS Code", "abre o Visual Studio Code".
Bonus: "abre o VS Code na pasta Mark-LV-main" → opens that folder in VS Code
(the folder is found by name, same as the file tools).
"""

import os
import shutil
import subprocess

PLUGIN = {
    "name": "abrir_vscode",
    "description": (
        "Opens Visual Studio Code (VS Code). Call when the user says 'abrir VS Code', "
        "'abre o VS Code', 'abre o Visual Studio Code', 'open VS Code'. If they name a "
        "folder or project ('abre o VS Code na pasta Mark-LV-main'), put it in 'folder' "
        "(a name, a shortcut like 'documents', a drive path like 'D:/Projetos', or a "
        "full path). Use this instead of open_app for VS Code."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "folder": {"type": "STRING",
                       "description": "Optional folder/project to open in VS Code"},
        },
        "required": [],
    },
}

_NO_WINDOW = 0x08000000


def _find_code() -> str | None:
    la = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    for p in (os.path.join(la, "Programs", "Microsoft VS Code", "Code.exe"),
              os.path.join(pf, "Microsoft VS Code", "Code.exe"),
              os.path.join(pf86, "Microsoft VS Code", "Code.exe")):
        if os.path.isfile(p):
            return p
    return shutil.which("code") or shutil.which("code.cmd")


def _resolve_folder(folder: str) -> str | None:
    if not folder:
        return None
    try:
        from actions.file_controller import _resolve_path
        p = _resolve_path(folder)
        return str(p) if p.exists() else None
    except Exception:
        return folder if os.path.isdir(folder) else None


def run(parameters: dict, player=None, session_memory=None) -> str:
    folder_arg = (parameters.get("folder") or "").strip()
    try:
        code = _find_code()
        if not code:
            return "VS Code was not found on this PC."
        folder = _resolve_folder(folder_arg)
        if folder_arg and not folder:
            return f"Folder '{folder_arg}' was not found."
        args = [code] + ([folder] if folder else [])
        if code.lower().endswith(".cmd"):
            subprocess.Popen(args, shell=True, creationflags=_NO_WINDOW)
        else:
            subprocess.Popen(args, close_fds=True)
        if player:
            try:
                player.write_log(f"SYS: Abrindo VS Code{(' em ' + folder) if folder else ''}")
            except Exception:
                pass
        return f"VS Code opened{(' in ' + folder) if folder else ''}."
    except Exception as e:
        return f"Could not open VS Code: {e}"
