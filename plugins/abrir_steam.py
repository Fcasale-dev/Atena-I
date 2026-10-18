"""
Plugin: abrir_steam — opens Steam, or launches an installed Steam game.

Say: "abrir Steam", "abre a Steam".
Bonus: "abre o jogo Counter-Strike na Steam" → launches that installed game.
"""

import glob
import os
import re
import subprocess

PLUGIN = {
    "name": "abrir_steam",
    "description": (
        "Opens Steam, or launches an INSTALLED Steam game by name. Call when the user "
        "says 'abrir Steam', 'abre a Steam', 'open Steam', or asks to open/play a game "
        "that is on Steam ('abre o Counter-Strike', 'jogar Elden Ring na Steam'). Put "
        "the game's name in 'game' (leave empty to just open Steam). Use this instead "
        "of open_app for Steam."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "game": {"type": "STRING",
                     "description": "Optional name of an installed game to launch"},
        },
        "required": [],
    },
}


def _steam_dir() -> str | None:
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                k = winreg.OpenKey(hive, key)
                for val in ("SteamPath", "InstallPath"):
                    try:
                        p = winreg.QueryValueEx(k, val)[0]
                        if p and os.path.isdir(p):
                            return os.path.normpath(p)
                    except OSError:
                        pass
            except OSError:
                pass
    except Exception:
        pass
    for p in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"):
        if os.path.isdir(p):
            return p
    return None


def _libraries(steam: str) -> list[str]:
    libs = [os.path.join(steam, "steamapps")]
    vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
    try:
        txt = open(vdf, encoding="utf-8", errors="ignore").read()
        for p in re.findall(r'"path"\s+"([^"]+)"', txt):
            libs.append(os.path.join(p.replace("\\\\", "\\"), "steamapps"))
    except Exception:
        pass
    return list(dict.fromkeys(libs))


def _installed_games(steam: str) -> dict[str, str]:
    games = {}
    for lib in _libraries(steam):
        for acf in glob.glob(os.path.join(lib, "appmanifest_*.acf")):
            try:
                txt = open(acf, encoding="utf-8", errors="ignore").read()
                appid = re.search(r'"appid"\s+"(\d+)"', txt)
                name = re.search(r'"name"\s+"([^"]+)"', txt)
                if appid and name:
                    games[name.group(1)] = appid.group(1)
            except Exception:
                pass
    return games


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _match(games: dict[str, str], wanted: str) -> tuple[str, str] | None:
    w = _norm(wanted)
    if not w:
        return None
    for name, appid in games.items():           # exact
        if _norm(name) == w:
            return name, appid
    for name, appid in games.items():           # contains
        if w in _norm(name) or _norm(name) in w:
            return name, appid
    import difflib                              # closest
    best = difflib.get_close_matches(w, [_norm(n) for n in games], n=1, cutoff=0.6)
    if best:
        for name, appid in games.items():
            if _norm(name) == best[0]:
                return name, appid
    return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    game = (parameters.get("game") or "").strip()
    try:
        steam = _steam_dir()
        if game:
            if not steam:
                return "Steam was not found on this PC."
            hit = _match(_installed_games(steam), game)
            if not hit:
                return f"No installed Steam game matches '{game}'."
            name, appid = hit
            os.startfile(f"steam://rungameid/{appid}")
            if player:
                try:
                    player.write_log(f"SYS: Abrindo {name} pela Steam")
                except Exception:
                    pass
            return f"Launching {name} on Steam."

        exe = os.path.join(steam, "steam.exe") if steam else None
        if exe and os.path.isfile(exe):
            subprocess.Popen([exe], close_fds=True)
        else:
            os.startfile("steam://open/main")
        if player:
            try:
                player.write_log("SYS: Abrindo Steam")
            except Exception:
                pass
        return "Steam opened."
    except Exception as e:
        return f"Could not open Steam: {e}"
