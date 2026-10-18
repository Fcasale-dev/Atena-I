import webbrowser
from urllib.parse import quote_plus


def weather_action(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:
    city     = parameters.get("city") or "São Carlos, SP, Brasil"
    when     = parameters.get("time", "today")

    if not isinstance(city, str) or not city.strip():
        city = "São Carlos, SP, Brasil"
    city = city.strip()

    # Real data first (Open-Meteo); the browser search is only the fallback.
    try:
        from core.weather import get_weather_text
        text = get_weather_text(city)
        _log(text.splitlines()[0], player)
        try:
            if player is not None and hasattr(player, "show_content"):
                player.show_content("CLIMA — " + city, text)
        except Exception:
            pass
        return (text + "\n\nSummarise this weather naturally for the user "
                "(now, today, and the week if they asked).")
    except Exception as e:
        print(f"[Weather] live data failed, falling back to browser: {e}")

    when = (when or "today").strip()

    search_query  = f"weather in {city} {when}"
    url           = f"https://www.google.com/search?q={quote_plus(search_query)}"

    try:
        opened = webbrowser.open(url)
        if not opened:
            raise RuntimeError("webbrowser.open returned False")
    except Exception as e:
        msg = f"Sir, I couldn't open the browser for the weather report: {e}"
        _log(msg, player)
        return msg

    msg = f"Showing the weather for {city}, {when}, sir."
    _log(msg, player)

    if session_memory:
        try:
            session_memory.set_last_search(query=search_query, response=msg)
        except Exception:
            pass

    return msg


def _log(message: str, player=None) -> None:
    print(f"[Weather] {message}")
    if player:
        try:
            player.write_log(f"ATENA: {message}")
        except Exception:
            pass


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "weather_report",
    "description": "Gives the real weather report (current, today and 7-day forecast). Default city: São Carlos, SP, Brasil.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "city": {
                "type": "STRING",
                "description": "City name. If the user does not say one, use São Carlos (the user's home city)."
            }
        },
        "required": []
    },
    "handler": weather_action,
}
