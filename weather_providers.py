import os
import requests
from typing import Optional, Dict

def mock_weather(city: str) -> Dict:
    # Keep a stable, testable demo path
    return {
        "city": city,
        "temp_f": 60,
        "condition": "cloudy",
        "precip_prob": 10,
        "when": "today",
    }

def open_meteo_weather(city: str, lat: float, lon: float) -> Dict:
    # Simple free API example (no key required); daily forecast
    # https://open-meteo.com/ — for demo purposes
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability"
        "&current_weather=true"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    temp_c = data.get("current_weather", {}).get("temperature")
    # if we only got C, convert to F
    temp_f = round((temp_c * 9/5) + 32) if isinstance(temp_c, (int, float)) else None

    # quick & simple precip prob (take next hour if present)
    probs = data.get("hourly", {}).get("precipitation_probability") or []
    precip_prob = probs[0] if probs else None

    return {
        "city": city,
        "temp_f": temp_f,
        "condition": "partly cloudy" if temp_f else "unknown",
        "precip_prob": precip_prob,
        "when": "today",
    }

def get_weather(city: str, lat: Optional[float]=None, lon: Optional[float]=None) -> Dict:
    use_live = os.getenv("USE_LIVE_WEATHER", "false").lower() == "true"
    if use_live and lat is not None and lon is not None:
        return open_meteo_weather(city, lat, lon)
    return mock_weather(city)
