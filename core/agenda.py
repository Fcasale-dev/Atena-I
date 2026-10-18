"""
core/agenda.py — ATENA's own calendar (local, config/agenda.json).

Entries: {"id", "date": "YYYY-MM-DD", "time": "HH:MM" | "", "text"}.
Past entries are pruned automatically after 30 days.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "config" / "agenda.json"
_lock = threading.Lock()


def _load() -> list[dict]:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    items = [i for i in items if i["date"] >= cutoff]
    items.sort(key=lambda i: (i["date"], i.get("time") or "99:99"))
    FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def add(day: str, text: str, time: str = "") -> dict:
    item = {"id": uuid.uuid4().hex[:8], "date": day, "time": time or "", "text": text}
    with _lock:
        items = _load()
        items.append(item)
        _save(items)
    return item


def between(start: str, end: str) -> list[dict]:
    with _lock:
        return [i for i in _load() if start <= i["date"] <= end]


def remove(words: str = "", day: str = "") -> int:
    with _lock:
        items = _load()
        ws = [w for w in (words or "").lower().split() if len(w) > 2]

        def match(i):
            if day and i["date"] != day:
                return False
            if words.lower() in ("all", "tudo", "todos"):
                return True
            return (not ws) or any(w in i["text"].lower() for w in ws)

        keep = [i for i in items if not match(i)]
        n = len(items) - len(keep)
        if n:
            _save(keep)
        return n


def today_text() -> str:
    """Short English line for the startup greeting, '' if nothing today."""
    t = date.today().isoformat()
    ev = between(t, t)
    if not ev:
        return ""
    return "; ".join((f"{e['time']} " if e.get("time") else "") + e["text"] for e in ev)
