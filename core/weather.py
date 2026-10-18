"""
Real weather data from Open-Meteo (free, no API key).

Default location is São Carlos, SP, Brazil. Returns a short plain-text summary
of today's weather and the forecast for the next 7 days, which the assistant
turns into natural speech.
"""

from __future__ import annotations

from datetime import datetime

import requests

DEFAULT_CITY = "São Carlos, SP, Brasil"
DEFAULT_LAT = -22.0175
DEFAULT_LON = -47.8908

_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

_WMO = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado",
    3: "nublado", 45: "neblina", 48: "neblina com geada",
    51: "garoa fraca", 53: "garoa", 55: "garoa forte",
    61: "chuva fraca", 63: "chuva", 65: "chuva forte",
    66: "chuva congelante", 67: "chuva congelante forte",
    71: "neve fraca", 73: "neve", 75: "neve forte",
    80: "pancadas de chuva fracas", 81: "pancadas de chuva", 82: "pancadas de chuva fortes",
    95: "trovoadas", 96: "trovoadas com granizo", 99: "trovoadas com granizo forte",
}


def _geocode(city: str):
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city.split(",")[0].strip(), "count": 1,
                "language": "pt", "format": "json"},
        timeout=6,
    )
    res = (r.json() or {}).get("results") or []
    if not res:
        return None
    g = res[0]
    label = ", ".join(x for x in (g.get("name"), g.get("admin1"), g.get("country")) if x)
    return g["latitude"], g["longitude"], label


def get_weather_text(city: str | None = None) -> str:
    """Today + 7-day forecast as compact text. Raises on network failure."""
    lat, lon, label = DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY
    if city and "carlos" not in city.lower():
        g = _geocode(city)
        if g:
            lat, lon, label = g

    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max",
            "timezone": "auto", "forecast_days": 7,
        },
        timeout=8,
    )
    r.raise_for_status()
    d = r.json()
    cur, day = d["current"], d["daily"]

    lines = [f"Clima em {label}:"]
    lines.append(
        f"Agora: {cur['temperature_2m']:.0f}°C (sensação {cur['apparent_temperature']:.0f}°C), "
        f"{_WMO.get(cur['weather_code'], 'tempo variável')}, "
        f"umidade {cur['relative_humidity_2m']}%, vento {cur['wind_speed_10m']:.0f} km/h."
    )
    for i, iso in enumerate(day["time"]):
        dt = datetime.strptime(iso, "%Y-%m-%d")
        nome = "Hoje" if i == 0 else ("Amanhã" if i == 1 else _DIAS[dt.weekday()].capitalize())
        chuva = day["precipitation_probability_max"][i]
        chuva_txt = f", chuva {chuva}%" if chuva is not None else ""
        lines.append(
            f"{nome} ({dt:%d/%m}): {day['temperature_2m_min'][i]:.0f}°–"
            f"{day['temperature_2m_max'][i]:.0f}°C, "
            f"{_WMO.get(day['weather_code'][i], 'tempo variável')}{chuva_txt}"
        )
    return "\n".join(lines)
