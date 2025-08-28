import os
import requests
from typing import Optional, Dict, Any

def mock_weather(city: str) -> Dict[str, Any]:
    # Stable demo response for local testing / CI
    return {
        "city": city,
        "temp_f": 60,
        "condition": "cloudy",
        "precip_prob": 10,
        "when": "today",
    }

def open_meteo_weather(city: str, lat: float, lon: float) -> Dict[str, Any]:
    """
    Simple free API example (no key required) — https://open-meteo.com/
    You can replace with any other provider later.
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true&hourly=precipitation_probability"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    temp_c = data.get("current_weather", {}).get("temperature")
    temp_f = round((temp_c * 9/5) + 32) if isinstance(temp_c, (int, float)) else None

    probs = data.get("hourly", {}).get("precipitation_probability") or []
    precip_prob = probs[0] if probs else None

    return {
        "city": city,
        "temp_f": temp_f,
        "condition": "partly cloudy" if temp_f is not None else "unknown",
        "precip_prob": precip_prob,
        "when": "today",
    }

def get_weather(city: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
    """
    Switches between mock/live modes based on USE_LIVE_WEATHER.
    - Live mode requires lat/lon to actually query Open-Meteo.
    - If lat/lon are missing, we just return mock data for now.
    - Later, you can add geocoding here to look up coords from the city name.
    """
    use_live = os.getenv("USE_LIVE_WEATHER", "false").lower() == "true"

    if use_live:
        if lat is not None and lon is not None:
            return open_meteo_weather(city, lat, lon)
        else:
            # Live mode requested but no coords given → fallback to mock
            # (future: plug in geocoding here to use `city`)
            return mock_weather(city)

    return mock_weather(city)
