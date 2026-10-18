"""
Plugin: escrever_email — ATENA writes an e-mail and leaves it ready in Brave.

  "Atena, escreve um e-mail pra Ana dizendo que a reunião mudou pra sexta"
     → opens Gmail's compose window in Brave with To, Subject and the message
       already filled in. NOTHING is sent: you review it and press Send yourself.
  "salva o e-mail da Ana: ana.souza@gmail.com"   → adds a contact
  "quais contatos você tem?" / "apaga o contato da Ana"

If the person is not in the contacts, the "To" field is left empty for you to
fill in (or say the address and she uses it directly).
Contacts live only on this PC, in config/contatos.txt — one per line,
"Nome = email". Edit it by hand any time; lines starting with # are ignored.
"""

import json
import os
import subprocess
import unicodedata
import webbrowser
from pathlib import Path
from urllib.parse import quote

PROVIDER = "gmail"          # "gmail" | "outlook" | "mailto"

_FILE = Path(__file__).resolve().parent.parent / "config" / "contatos.txt"

_HEADER = """# Contatos da ATENA — um por linha, no formato:  Nome = email
# Ex.:  Ana = ana.souza@gmail.com
# Pode editar à vontade. Linhas com # são ignoradas.
"""

PLUGIN = {
    "name": "escrever_email",
    "description": (
        "Drafts an e-mail and opens it ready in the browser for the user to review — "
        "it NEVER sends. action='compose' when the user asks to write/send an e-mail: "
        "'escreve um e-mail pra Ana dizendo X', 'manda um e-mail pro meu professor "
        "sobre Y'. YOU write the message: 'to' = the person's name as said (or an "
        "e-mail address if spoken), 'subject' = a short fitting subject, 'body' = the "
        "full, well-written e-mail in Portuguese (greeting, message, sign-off with the "
        "user's name 'Felipe' unless told otherwise; tone formal or casual to fit the "
        "person). action='save_contact' with 'name' and 'email' for 'salva o e-mail da "
        "Ana: ...'. action='list_contacts' / 'delete_contact' (with 'name'). After "
        "compose, tell the user it is open in Brave to review and that they press "
        "Send; if the contact was unknown, say the To field is empty."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "compose | save_contact | list_contacts | delete_contact"},
            "to": {"type": "STRING", "description": "Recipient name or e-mail address"},
            "subject": {"type": "STRING", "description": "E-mail subject"},
            "body": {"type": "STRING", "description": "Full e-mail text"},
            "name": {"type": "STRING", "description": "Contact name (save/delete)"},
            "email": {"type": "STRING", "description": "Contact e-mail address (save)"},
        },
        "required": ["action"],
    },
}


def _key(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def _load() -> dict:
    """{normalised name: {"name", "email"}} from contatos.txt."""
    out = {}
    try:
        for line in _FILE.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sep = "=" if "=" in line else (":" if ":" in line else None)
            if not sep:
                continue
            name, addr = [x.strip() for x in line.split(sep, 1)]
            if name and "@" in addr:
                out[_key(name)] = {"name": name, "email": addr.replace(" ", "")}
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[Email] could not read contacts: {e}")
    return out


def _save(c: dict) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{v['name']} = {v['email']}" for v in sorted(c.values(), key=lambda v: v["name"].lower())]
    _FILE.write_text(_HEADER + "\n".join(lines) + "\n", encoding="utf-8")


def _lookup(to: str):
    """(address, display name) — address '' if unknown."""
    to = (to or "").strip()
    if "@" in to:
        return to.replace(" ", ""), to
    c = _load()
    k = _key(to)
    for prefix in ("o ", "a ", "pro ", "pra ", "para "):
        if k.startswith(prefix):
            k = k[len(prefix):]
    if k in c:
        return c[k]["email"], c[k]["name"]
    for ck, v in c.items():                         # partial: "professor" → "professor joão"
        if k and (k in ck or ck in k):
            return v["email"], v["name"]
    return "", to


def _open(url: str) -> None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "abrir_brave_tmp", Path(__file__).with_name("abrir_brave.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        brave = mod._find_brave()
        if brave and brave.lower().endswith(".exe"):
            subprocess.Popen([brave, url], close_fds=True)
            return
    except Exception:
        pass
    webbrowser.open(url)


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "compose").strip().lower()

    if action == "save_contact":
        name, addr = (parameters.get("name") or "").strip(), (parameters.get("email") or "").strip()
        addr = addr.replace(" ", "").replace("arroba", "@")
        if not name or "@" not in addr:
            return "Need a name and a valid e-mail address to save the contact."
        c = _load()
        c[_key(name)] = {"name": name, "email": addr}
        _save(c)
        return f"Contact saved: {name} <{addr}>."

    if action == "list_contacts":
        c = _load()
        if not c:
            return "No contacts saved yet."
        return "Contacts:\n" + "\n".join(f"- {v['name']}: {v['email']}" for v in c.values())

    if action == "delete_contact":
        c = _load()
        k = _key(parameters.get("name", ""))
        if k in c:
            gone = c.pop(k)
            _save(c)
            return f"Contact removed: {gone['name']}."
        return "Contact not found."

    # compose
    addr, who = _lookup(parameters.get("to", ""))
    subject = (parameters.get("subject") or "").strip()
    body = (parameters.get("body") or "").strip()
    if not body:
        return "What should the e-mail say?"
    if PROVIDER == "outlook":
        url = (f"https://outlook.live.com/mail/0/deeplink/compose?to={quote(addr)}"
               f"&subject={quote(subject)}&body={quote(body)}")
    elif PROVIDER == "mailto":
        url = f"mailto:{quote(addr)}?subject={quote(subject)}&body={quote(body)}"
    else:
        url = (f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(addr)}"
               f"&su={quote(subject)}&body={quote(body)}")
    _open(url)
    if player:
        try:
            player.write_log(f"SYS: ✉️ Rascunho aberto no Brave — para: {addr or '(vazio)'} | assunto: {subject}")
        except Exception:
            pass
    note = "" if addr else (f" '{who}' is not in the contacts, so the To field is EMPTY — "
                            "ask the user to fill it in (and offer to save the contact).")
    return f"Draft open in Brave for review (not sent). To: {addr or '—'}. Subject: {subject}.{note}"
