"""
Plugin: humor — the owl HUD reacts to how you talk to ATENA.

  * compliments ("você é incrível", "boa, Atena", "obrigado, Atena, mandou bem")
      → happy: eyes turn into smiling arcs, hearts and sparkles float up,
        the 3D owl bobs her head and flaps happily
  * "boa noite, Atena" → she says good night, closes her eyes slowly,
        z's float up, and she goes back to the tray to sleep
  * "bom dia, Atena"   → wakes up bright, with sparkles

At night (23:00–06:00) she also sleeps "for real" on her own: when idle she is
a little drowsy, and while asleep she tucks in and floats z's.
"""

PLUGIN = {
    "name": "humor",
    "description": (
        "Makes ATENA's owl HUD react emotionally. Call with mood='happy' when the user "
        "compliments or thanks you warmly ('você é incrível', 'boa, Atena', 'mandou "
        "bem', 'te amo, Atena', 'obrigado, você é demais'); mood='goodnight' when the "
        "user says 'boa noite, Atena' / 'vou dormir'; mood='goodmorning' for 'bom dia, "
        "Atena'. Call it silently alongside your normal short reply."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "mood": {"type": "STRING", "description": "happy | goodnight | goodmorning"},
        },
        "required": ["mood"],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    mood = (parameters.get("mood") or "happy").strip().lower()
    if mood not in ("happy", "goodnight", "goodmorning"):
        mood = "happy"
    if player is not None and hasattr(player, "set_mood"):
        try:
            player.set_mood(mood)
        except Exception:
            pass
    if mood == "goodnight":
        return ("Owl is going to sleep. Wish the user a warm, short good night in "
                "Portuguese (e.g. 'Boa noite, senhor. Durma bem.'), then call "
                "go_to_background.")
    if mood == "goodmorning":
        return "Owl woke up happy. Reply with a short, cheerful good morning."
    return "Owl is happy. Reply naturally and briefly, warmly acknowledging the compliment."
