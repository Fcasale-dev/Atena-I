"""
Plugin: agenda — ATENA's calendar.

  "Atena, anota que dia 25 vou ao dentista às 14h"
  "dia 3 anota: prova de cálculo"
  "o que tenho amanhã?" / "o que tenho essa semana?" / "minha agenda de novembro"
  "tira o dentista da agenda" / "apaga tudo do dia 25"

On the day itself she mentions it in the morning greeting, and if the entry has
a time she also sets a spoken reminder 30 minutes before.
"""

import calendar as _cal
from datetime import date, datetime, timedelta

from core import agenda

PLUGIN = {
    "name": "agenda",
    "description": (
        "The user's calendar/agenda. action='add' when they ask to note something on "
        "a day: 'anota que dia 25 vou ao dentista', 'dia 3 anota prova de cálculo', "
        "'marca na agenda sexta reunião às 10h'. Give 'date' as YYYY-MM-DD (work it "
        "out from today's date: 'amanhã', 'sexta que vem', 'dia 25' = this month, or "
        "next month if that day already passed), optional 'time' HH:MM, and 'text' "
        "(what will happen, short, Portuguese). action='list' for 'o que tenho "
        "amanhã/hoje/essa semana/em novembro' with 'date' (start) and optional "
        "'end_date'. action='remove' with 'text' words and/or 'date' ('all' clears "
        "that day). Confirm briefly, saying the weekday and date."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add | list | remove"},
            "date": {"type": "STRING", "description": "YYYY-MM-DD"},
            "end_date": {"type": "STRING", "description": "YYYY-MM-DD, for list ranges"},
            "time": {"type": "STRING", "description": "HH:MM (optional)"},
            "text": {"type": "STRING", "description": "What happens / words to remove"},
        },
        "required": ["action"],
    },
}

_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _pt(d: str) -> str:
    dt = date.fromisoformat(d)
    return f"{_DIAS[dt.weekday()]}, {dt:%d/%m/%Y}"


def _valid(d: str) -> str | None:
    try:
        return date.fromisoformat((d or "").strip()).isoformat()
    except Exception:
        return None


def _set_reminder(day: str, hhmm: str, text: str) -> str:
    """Spoken reminder 30 min before, through the lembretes plugin's store."""
    try:
        when = datetime.fromisoformat(f"{day}T{hhmm}") - timedelta(minutes=30)
        if when <= datetime.now():
            return ""
        import core
        lem_run = getattr(core, "LEMBRETES_RUN", None)   # published by plugins/lembretes.py
        if lem_run is None:
            return ""
        lem_run({"action": "add", "message": f"daqui a 30 minutos: {text}",
                 "at_time": when.strftime("%H:%M"), "date": when.strftime("%Y-%m-%d")})
        return " A spoken reminder was also set 30 minutes before."
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "add").strip().lower()
    text = (parameters.get("text") or "").strip()
    day = _valid(parameters.get("date", ""))
    hhmm = (parameters.get("time") or "").strip().replace("h", ":")
    if hhmm and len(hhmm.split(":")[0]) == 1:
        hhmm = "0" + hhmm
    if hhmm and ":" not in hhmm:
        hhmm += ":00"
    if hhmm.endswith(":"):
        hhmm += "00"

    if action == "add":
        if not day:
            return "Which day? (give the date as YYYY-MM-DD)"
        if not text:
            return "What should I note on that day?"
        agenda.add(day, text, hhmm)
        extra = _set_reminder(day, hhmm, text) if hhmm else ""
        if player:
            try:
                player.write_log(f"SYS: 📅 Agenda: {_pt(day)}{(' ' + hhmm) if hhmm else ''} — {text}")
            except Exception:
                pass
        return f"Noted on {_pt(day)}{(' at ' + hhmm) if hhmm else ''}: {text}.{extra}"

    if action == "list":
        start = day or date.today().isoformat()
        end = _valid(parameters.get("end_date", "")) or start
        if end < start:
            start, end = end, start
        ev = agenda.between(start, end)
        if not ev:
            return f"Nothing on the agenda from {_pt(start)} to {_pt(end)}." if start != end \
                else f"Nothing on the agenda for {_pt(start)}."
        return "Agenda:\n" + "\n".join(
            f"- {_pt(e['date'])}{(' ' + e['time']) if e.get('time') else ''}: {e['text']}" for e in ev)

    if action == "remove":
        n = agenda.remove(text, day or "")
        return f"Removed {n} item(s) from the agenda." if n else "Nothing matching found on the agenda."

    return "Unknown agenda action."
