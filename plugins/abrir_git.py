"""
Plugin: abrir_git — opens Git Bash, optionally already inside a folder.

  "abrir o Git"                                   → Git Bash in your home folder
  "abrir o Git na pasta Mark-LV-main"             → Git Bash inside that folder
  "abrir o Git na pasta Projetos no disco D"      → finds Projetos on D: and opens there

The folder is found by name with the same instant folder index the file tools
use, so the full path is never needed (it still works if you say it).
"""

import glob
import os
import shutil
import subprocess

PLUGIN = {
    "name": "abrir_git",
    "description": (
        "Opens Git Bash. Call when the user says 'abrir o Git', 'abre o Git Bash', "
        "'abre o terminal do Git'. If they name a folder, put its name in 'folder' "
        "(a name like 'Mark-LV-main', a partial path like 'Projetos/Faculdade' or a full "
        "path) and the drive in 'drive' if they say one ('D'). Git Bash then starts "
        "inside that folder. Use this instead of open_app for Git."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "folder": {"type": "STRING", "description": "Optional folder to open Git Bash in"},
            "drive": {"type": "STRING", "description": "Optional drive letter, e.g. 'D'"},
        },
        "required": [],
    },
}


def _find_git_bash() -> str | None:
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    la = os.environ.get("LOCALAPPDATA", "")
    for p in (os.path.join(pf, "Git", "git-bash.exe"),
              os.path.join(pf86, "Git", "git-bash.exe"),
              os.path.join(la, "Programs", "Git", "git-bash.exe")):
        if os.path.isfile(p):
            return p
    git = shutil.which("git")                    # …\Git\cmd\git.exe → …\Git\git-bash.exe
    if git:
        cand = os.path.join(os.path.dirname(os.path.dirname(git)), "git-bash.exe")
        if os.path.isfile(cand):
            return cand
    for lnk in glob.glob(os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                                      r"Microsoft\Windows\Start Menu\Programs\**\Git Bash*.lnk"),
                         recursive=True):
        return lnk
    return None


def _resolve(folder: str, drive: str) -> str | None:
    folder = (folder or "").strip()
    drive = (drive or "").strip().rstrip(":").upper()
    if not folder and not drive:
        return None
    raw = f"{drive}:/{folder}" if drive else folder
    try:
        from actions.file_controller import _resolve_path
        p = _resolve_path(raw)
        return str(p) if p.exists() and p.is_dir() else None
    except Exception:
        return raw if os.path.isdir(raw) else None


def run(parameters: dict, player=None, session_memory=None) -> str:
    folder_arg = parameters.get("folder", "")
    drive_arg = parameters.get("drive", "")
    try:
        exe = _find_git_bash()
        if not exe:
            return "Git Bash was not found on this PC (is Git for Windows installed?)."
        target = _resolve(folder_arg, drive_arg)
        if (folder_arg or drive_arg) and not target:
            where = f"{folder_arg} {('no disco ' + drive_arg) if drive_arg else ''}".strip()
            return f"Folder '{where}' was not found."
        if exe.lower().endswith(".lnk"):
            os.startfile(exe)                    # shortcut fallback: cannot pass a folder
        else:
            args = [exe, f"--cd={target}"] if target else [exe, "--cd-to-home"]
            subprocess.Popen(args, close_fds=True)
        if player:
            try:
                player.write_log(f"SYS: Abrindo Git Bash{(' em ' + target) if target else ''}")
            except Exception:
                pass
        return f"Git Bash opened{(' in ' + target) if target else ''}."
    except Exception as e:
        return f"Could not open Git Bash: {e}"
