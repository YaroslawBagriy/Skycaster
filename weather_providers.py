# weather_providers.py
import os
import requests
from typing import Optional, Dict, Any, Tuple

def mock_weather(city: str) -> Dict[str, Any]:
    return {"city": city, "temp_f": 60, "condition": "cloudy", "precip_prob": 10, "when": "today"}

def geocode_city(city: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Minimal geocoder using Open-Meteo's free geocoding API.
    Returns (lat, lon) or (None, None) if not found.
    """
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        if not results:
            return None, None
        return results[0].get("latitude"), results[0].get("longitude")
    except Exception:
        return None, None

def open_meteo_weather(city: str, lat: float, lon: float) -> Dict[str, Any]:
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
    Live mode:
      - If lat/lon provided, use them.
      - Else geocode the city -> lat/lon.
      - If geocoding fails, fallback to mock.
    """
    use_live = os.getenv("USE_LIVE_WEATHER", "false").lower() == "true"

    if use_live:
        # Use coords if we have them; otherwise try geocoding.
        if lat is None or lon is None:
            glat, glon = geocode_city(city)
            lat = lat if lat is not None else glat
            lon = lon if lon is not None else glon

        if lat is not None and lon is not None:
            return open_meteo_weather(city, lat, lon)

        # Live requested but we couldn't get coords → graceful fallback
        return mock_weather(city)

    # Not in live mode → mock
    return mock_weather(city)