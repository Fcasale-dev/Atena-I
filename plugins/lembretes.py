"""
Plugin: lembretes — natural spoken reminders, handled by ATENA herself.

  "me lembra de tirar a pizza do forno daqui a 20 minutos"   → in 20 min
  "daqui 2 horas me lembra de ligar pra minha mãe"           → in 2 h
  "me avisa às 18h que tenho aula"                           → today 18:00 (or tomorrow)
  "me lembra de beber água a cada 1 hora"                    → every hour
  "quais lembretes eu tenho?" / "cancela o lembrete da água" / "cancela todos"

When the time comes ATENA SAYS the reminder out loud (even from the tray) and
shows a Windows notification. Reminders are saved in config/lembretes.json, so
they survive a restart; one missed while ATENA was closed is announced (late)
the next time she starts, if it is less than 12 hours old.
"""

import json
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

PLUGIN = {
    "name": "lembretes",
    "description": (
        "Spoken reminders. Use this (NOT the 'reminder' tool) whenever the user asks to "
        "be reminded or warned of something: 'me lembra de X daqui a 20 minutos', "
        "'daqui 2 horas me lembra de X', 'me avisa às 18h que tenho aula', 'me lembra "
        "de beber água a cada 1 hora'. action='add' with 'message' (what to remind, "
        "short, in Portuguese) and ONE of: 'in_minutes' (relative: convert hours to "
        "minutes, e.g. 2 h → 120), 'at_time' ('HH:MM' 24h, optional 'date' "
        "'YYYY-MM-DD'), or 'every_minutes' for repeating ones (can be combined with "
        "in_minutes/at_time for the first time). action='list' for 'quais lembretes "
        "tenho'. action='cancel' with 'message' (words of the reminder) or 'all'. "
        "Confirm in one short sentence saying when it will fire."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add | list | cancel"},
            "message": {"type": "STRING", "description": "What to remind / which one to cancel ('all' = every reminder)"},
            "in_minutes": {"type": "NUMBER", "description": "Fire after this many minutes"},
            "at_time": {"type": "STRING", "description": "Fire at this time, 'HH:MM' 24h"},
            "date": {"type": "STRING", "description": "Optional date for at_time, 'YYYY-MM-DD'"},
            "every_minutes": {"type": "NUMBER", "description": "Repeat every N minutes"},
        },
        "required": ["action"],
    },
}

_FILE = Path(__file__).resolve().parent.parent / "config" / "lembretes.json"
_LOCK = threading.Lock()
_ITEMS: list[dict] = []
_STARTED = False


# ── storage ─────────────────────────────────────────────────────────────────
def _load():
    global _ITEMS
    try:
        _ITEMS = json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        _ITEMS = []


def _save():
    try:
        _FILE.parent.mkdir(parents=True, exist_ok=True)
        _FILE.write_text(json.dumps(_ITEMS, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        print(f"[Lembretes] save failed: {e}")


# ── firing ──────────────────────────────────────────────────────────────────
def _ui():
    try:
        from ui import JarvisUI
        return getattr(JarvisUI, "_instance", None)
    except Exception:
        return None


def _fire(item: dict, late_min: int = 0) -> None:
    msg = item["msg"]
    ui = _ui()
    print(f"[Lembretes] ⏰ {msg}")
    if ui is None:
        return
    try:
        ui.write_log(f"SYS: ⏰ Lembrete: {msg}")
    except Exception:
        pass
    try:
        ui.notify("⏰ Lembrete", msg)
    except Exception:
        pass
    late = (f" (It was due {late_min} minutes ago while you were closed — mention it "
            "was late.)") if late_min > 1 else ""
    say = getattr(ui, "request_say", None)
    if say:
        try:
            say(f"[REMINDER] It is time for a reminder the user asked for: \"{msg}\". "
                f"Tell the user now, in ONE short natural sentence in Brazilian "
                f"Portuguese, starting with something like 'Senhor, lembrete:'. Do not "
                f"call any tools.{late}")
        except Exception:
            pass


def _loop():
    first = True
    while True:
        now = time.time()
        due = []
        with _LOCK:
            keep = []
            for it in _ITEMS:
                if it["due"] <= now:
                    late = int((now - it["due"]) // 60)
                    if first and late > 12 * 60 and not it.get("every"):
                        continue                          # too old, drop silently
                    due.append((dict(it), late if first else 0))
                    if it.get("every"):
                        step = it["every"]
                        while it["due"] <= now:
                            it["due"] += step
                        keep.append(it)
                else:
                    keep.append(it)
            if due or len(keep) != len(_ITEMS):
                _ITEMS[:] = keep
                _save()
        for it, late in due:
            if it.get("every") and late > it["every"] / 60:
                late = 0                                  # repeating: just say it once now
            _fire(it, late)
            time.sleep(1.5)                               # don't stack several at once
        first = False
        time.sleep(5)


def _start():
    global _STARTED
    if _STARTED:
        return
    _STARTED = True
    _load()
    threading.Thread(target=_loop, daemon=True, name="Lembretes").start()


_start()    # runs when ATENA loads her plugins at startup


# ── helpers ─────────────────────────────────────────────────────────────────
def _fmt_when(ts: float) -> str:
    d = datetime.fromtimestamp(ts)
    now = datetime.now()
    mins = max(0, int(round((ts - time.time()) / 60)))
    rel = f"{mins} min" if mins < 60 else f"{mins // 60} h {mins % 60:02d} min"
    day = "" if d.date() == now.date() else (
        " amanhã" if d.date() == (now + timedelta(days=1)).date() else d.strftime(" em %d/%m"))
    return f"{d:%H:%M}{day} (daqui a {rel})"


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None


# ── tool entry point ────────────────────────────────────────────────────────
def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "add").strip().lower()
    msg = (parameters.get("message") or "").strip()

    if action == "list":
        with _LOCK:
            items = sorted(_ITEMS, key=lambda i: i["due"])
        if not items:
            return "No reminders set."
        lines = [f"- {i['msg']} → {_fmt_when(i['due'])}"
                 + (f", repeats every {int(i['every'] // 60)} min" if i.get("every") else "")
                 for i in items]
        return "Reminders:\n" + "\n".join(lines)

    if action == "cancel":
        with _LOCK:
            if msg.lower() in ("all", "todos", "tudo", ""):
                n = len(_ITEMS)
                _ITEMS.clear()
            else:
                words = [w for w in msg.lower().split() if len(w) > 2]
                before = len(_ITEMS)
                _ITEMS[:] = [i for i in _ITEMS
                             if not any(w in i["msg"].lower() for w in words)]
                n = before - len(_ITEMS)
            _save()
        return f"Cancelled {n} reminder(s)." if n else "No matching reminder found."

    # add
    if not msg:
        return "What should I remind you about?"
    in_min = _num(parameters.get("in_minutes"))
    every = _num(parameters.get("every_minutes"))
    at = (parameters.get("at_time") or "").strip()
    now = datetime.now()
    due = None
    if at:
        try:
            hh, mm = [int(x) for x in at.replace("h", ":").split(":")[:2] + ["0"]][:2]
            day = now.date()
            if parameters.get("date"):
                day = datetime.strptime(parameters["date"], "%Y-%m-%d").date()
            dt = datetime.combine(day, datetime.min.time()).replace(hour=hh, minute=mm)
            if dt <= now and not parameters.get("date"):
                dt += timedelta(days=1)
            due = dt.timestamp()
        except Exception:
            return f"Could not understand the time '{at}'."
    elif in_min is not None:
        due = time.time() + max(0.1, in_min) * 60
    elif every:
        due = time.time() + every * 60
    else:
        return "When should I remind you? (in how long, at what time, or how often)"

    item = {"id": uuid.uuid4().hex[:8], "msg": msg, "due": due,
            "every": every * 60 if every else 0}
    with _LOCK:
        _ITEMS.append(item)
        _save()
    when = _fmt_when(due)
    rep = f", then every {int(every)} min" if every else ""
    if player:
        try:
            player.write_log(f"SYS: ⏰ Lembrete criado: {msg} — {when}{rep}")
        except Exception:
            pass
    return f"Reminder set: '{msg}' at {when}{rep}."


# let other plugins (agenda) create reminders through this one
try:
    import core as _core
    _core.LEMBRETES_RUN = run
except Exception:
    pass
