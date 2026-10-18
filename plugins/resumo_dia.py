"""
Plugin: resumo_dia — end-of-day summary.

  "como foi meu dia?", "resumo do dia", "quanto tempo fiquei no VS Code hoje?",
  "resumo de ontem"

Uses core/activity.py, which quietly notes the program in the foreground every
5 s (not counting time away from the PC) and every command ATENA ran.
"""

import threading
from collections import Counter
from datetime import date, datetime, timedelta

from core import activity

activity.start()

PLUGIN = {
    "name": "resumo_dia",
    "description": (
        "End-of-day summary of what the user did on the PC: active time, time spent "
        "in each program, and what ATENA did for them. Call for 'como foi meu dia?', "
        "'resumo do dia', 'o que eu fiz hoje?', 'quanto tempo fiquei no <programa>?', "
        "'resumo de ontem' (day='ontem'). Answer in Portuguese, in a natural short "
        "paragraph: total active time, the top 3–5 programs with their times, and a "
        "line about what ATENA did. A dry witty remark at the end is welcome."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "day": {"type": "STRING", "description": "hoje (default) | ontem | YYYY-MM-DD"},
        },
        "required": [],
    },
}

_TOOL_PT = {
    "open_app": "abrir programas", "abrir_steam": "abrir a Steam/jogos",
    "abrir_vscode": "abrir o VS Code", "abrir_brave": "abrir o Brave",
    "abrir_claude": "abrir o Claude", "abrir_git": "abrir o Git",
    "file_controller": "pastas e arquivos", "web_search": "pesquisas",
    "weather_report": "clima", "lembretes": "lembretes", "modo_jogo": "modo jogo",
    "status_pc": "status do PC", "system_status": "status do PC",
    "saida_audio": "troca de som", "computer_settings": "ajustes do PC",
    "youtube_video": "vídeos", "browser_control": "navegador",
}


def _fmt(sec: float) -> str:
    m = int(round(sec / 60))
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d} min"


def run(parameters: dict, player=None, session_memory=None) -> str:
    raw = (parameters.get("day") or "hoje").strip().lower()
    if raw in ("ontem", "yesterday"):
        d = date.today() - timedelta(days=1)
    elif raw in ("hoje", "today", ""):
        d = date.today()
    else:
        try:
            d = date.fromisoformat(raw)
        except Exception:
            d = date.today()

    s = activity.summary(d)
    apps = {k: v for k, v in s["apps"].items() if k != "ATENA" and v >= 60}
    if not apps and not s["actions"]:
        return f"No activity recorded for {d.isoformat()} yet."

    total = sum(apps.values())
    top = sorted(apps.items(), key=lambda kv: -kv[1])[:8]
    lines = [f"Date: {d.isoformat()}",
             f"Active time on the PC: {_fmt(total)} (from {s['first']} to {s['last']})",
             "Time per program: " + "; ".join(f"{a}: {_fmt(t)}" for a, t in top)]

    acts = Counter(_TOOL_PT.get(t, t) for _h, t, _a in s["actions"])
    if acts:
        lines.append(f"ATENA ran {sum(acts.values())} commands: " +
                     ", ".join(f"{n}× {what}" for what, n in acts.most_common(6)))

    # End-of-day summary given → forget that day a few seconds later, so the
    # log never piles up. (Earlier in the day it is kept, so the rest of the
    # day still counts.)
    end_of_day = d < date.today() or datetime.now().hour >= 18
    if end_of_day:
        threading.Timer(5.0, activity.clear, args=(d,)).start()
        lines.append("(This day's activity log will now be erased.)")
    return "\n".join(lines)
