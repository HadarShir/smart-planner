"""
Weather module — uses Open-Meteo (free, no API key required).

Geocoding:  https://geocoding-api.open-meteo.com
Forecast:   https://api.open-meteo.com
"""

import datetime
import requests
import streamlit as st

# WMO Weather Interpretation Codes
_WMO = {
    0:  ("☀️",  "Clear sky"),
    1:  ("🌤",  "Mainly clear"),
    2:  ("⛅",  "Partly cloudy"),
    3:  ("☁️",  "Overcast"),
    45: ("🌫",  "Foggy"),
    48: ("🌫",  "Icy fog"),
    51: ("🌦",  "Light drizzle"),
    53: ("🌦",  "Drizzle"),
    55: ("🌧",  "Heavy drizzle"),
    61: ("🌧",  "Light rain"),
    63: ("🌧",  "Rain"),
    65: ("🌧",  "Heavy rain"),
    71: ("🌨",  "Light snow"),
    73: ("🌨",  "Snow"),
    75: ("❄️",  "Heavy snow"),
    80: ("🌧",  "Rain showers"),
    81: ("🌧",  "Heavy showers"),
    82: ("⛈",  "Violent showers"),
    95: ("⛈",  "Thunderstorm"),
    96: ("⛈",  "Thunderstorm + hail"),
    99: ("⛈",  "Severe thunderstorm"),
}

# Common Hebrew/local → international name mapping
_CITY_ALIASES = {
    "באר שבע":   "Beersheba",
    "תל אביב":   "Tel Aviv",
    "ירושלים":   "Jerusalem",
    "חיפה":      "Haifa",
    "אילת":      "Eilat",
    "נתניה":     "Netanya",
    "פתח תקווה": "Petah Tikva",
    "ראשון לציון":"Rishon LeZion",
    "אשדוד":     "Ashdod",
    "אשקלון":    "Ashkelon",
    "רחובות":    "Rehovot",
    "הרצליה":    "Herzliya",
    "חולון":     "Holon",
    "beer sheva":  "Beersheba",
    "be'er sheva": "Beersheba",
    "beer-sheva":  "Beersheba",
    "tel aviv":    "Tel Aviv",
}


def _wmo_info(code: int) -> tuple:
    """Return (icon, description) for a WMO weather code."""
    for threshold in sorted(_WMO.keys(), reverse=True):
        if code >= threshold:
            return _WMO[threshold]
    return ("🌡", "Unknown")


def _normalize_city(city: str) -> str:
    """Translate local/alias names to the international name the API recognises."""
    return _CITY_ALIASES.get(city.strip(), _CITY_ALIASES.get(city.strip().lower(), city.strip()))


def _geocode_once(city: str):
    """Return (lat, lon) or (None, None). Not cached so failures can be retried."""
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        )
        results = r.json().get("results", [])
        if results:
            return results[0]["latitude"], results[0]["longitude"]
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=3600)
def get_weekly_weather(city: str) -> list:
    """
    Return a list of 7 dicts (today + 6 days).
    Only caches successful results; failures return [] without caching.
    """
    if not city or not city.strip():
        return []

    normalized = _normalize_city(city)
    lat, lon   = _geocode_once(normalized)

    # If normalized name failed, try original as-is
    if lat is None and normalized != city.strip():
        lat, lon = _geocode_once(city.strip())

    if lat is None:
        return []

    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lon,
                "daily": ",".join([
                    "weathercode",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "windspeed_10m_max",
                ]),
                "timezone":      "auto",
                "forecast_days": 7,
            },
            timeout=8,
        )
        daily = r.json().get("daily", {})
        if not daily.get("time"):
            return []
    except Exception:
        return []

    result = []
    for i, date_str in enumerate(daily["time"]):
        code             = daily["weathercode"][i]
        icon, condition  = _wmo_info(code)
        temp_max         = daily["temperature_2m_max"][i]
        temp_min         = daily["temperature_2m_min"][i]
        precip           = daily.get("precipitation_sum", [0] * 7)[i] or 0
        wind             = daily.get("windspeed_10m_max",  [0] * 7)[i] or 0

        tips = []
        if precip > 1:
            tips.append("☂️ קח מטרייה")
        if temp_max < 10:
            tips.append("🧥 לבוש חם")
        elif temp_max < 18:
            tips.append("🧣 ג'קט קל")
        elif temp_max > 32:
            tips.append("🥤 שתה הרבה מים")
        if wind > 40:
            tips.append("💨 רוח חזקה")
        if not tips:
            tips.append("✅ מזג אוויר נעים")

        d   = datetime.date.fromisoformat(date_str)
        dow = (d.weekday() + 1) % 7   # Sun=0 … Sat=6

        result.append({
            "date":      date_str,
            "dow":       dow,
            "icon":      icon,
            "condition": condition,
            "temp_max":  round(temp_max),
            "temp_min":  round(temp_min),
            "precip":    round(precip, 1),
            "tip":       " · ".join(tips),
        })

    return result
