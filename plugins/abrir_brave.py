"""
Plugin: abrir_brave — opens the Brave browser.

Say: "abrir Brave", "abre o navegador", "abra meu navegador".
Optional: "abre o Brave no YouTube" → opens that site in Brave.
"""

import glob
import os
import subprocess

PLUGIN = {
    "name": "abrir_brave",
    "description": (
        "Opens the Brave web browser (the user's browser). Call when the user says "
        "'abrir Brave', 'abre o Brave', 'abre o navegador', 'abra meu navegador', "
        "'open Brave'. If they name a site ('abre o Brave no YouTube'), pass it in "
        "'url'. Use this instead of open_app for Brave / 'o navegador'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING",
                    "description": "Optional site or address to open, e.g. 'youtube.com'"},
        },
        "required": [],
    },
}


def _find_brave() -> str | None:
    la = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    rel = os.path.join("BraveSoftware", "Brave-Browser", "Application", "brave.exe")
    for base in (pf, pf86, la):
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            return p
    # Start Menu shortcut as a fallback
    for r in (os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
              os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                           r"Microsoft\Windows\Start Menu\Programs")):
        for lnk in glob.glob(os.path.join(r, "**", "Brave*.lnk"), recursive=True):
            return lnk
    return None


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if "://" not in u:
        if "." not in u:                 # "youtube" → youtube.com
            u = u.replace(" ", "") + ".com"
        u = "https://" + u
    return u


def run(parameters: dict, player=None, session_memory=None) -> str:
    url = _normalize_url(parameters.get("url", ""))
    try:
        brave = _find_brave()
        if brave is None:
            return "Brave was not found on this PC."
        if brave.lower().endswith(".lnk"):
            if url:
                # a shortcut can't take arguments here — open Brave, then the site
                os.startfile(brave)
            else:
                os.startfile(brave)
        else:
            subprocess.Popen([brave] + ([url] if url else []), close_fds=True)
        if player:
            try:
                player.write_log(f"SYS: Abrindo Brave{(' em ' + url) if url else ''}")
            except Exception:
                pass
        return f"Brave opened{(' at ' + url) if url else ''}."
    except Exception as e:
        return f"Could not open Brave: {e}"
