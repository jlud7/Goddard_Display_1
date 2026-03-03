import requests


def get_weather_fun(location: str = "Miami,FL", units: str = "imperial") -> dict:
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        ).json()
    except (requests.RequestException, ValueError):
        return {"ok": False, "error": "geocode_request_failed"}

    if not geo.get("results"):
        return {"ok": False, "error": "geocode_failed"}

    r = geo["results"][0]
    lat, lon = r["latitude"], r["longitude"]

    temp_unit = "fahrenheit" if units == "imperial" else "celsius"
    wind_unit = "mph" if units == "imperial" else "kmh"

    try:
        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "temperature_unit": temp_unit,
                "wind_speed_unit": wind_unit,
                "timezone": "auto",
            },
            timeout=10,
        ).json()
    except (requests.RequestException, ValueError):
        return {"ok": False, "error": "weather_request_failed"}

    cur = wx.get("current") or {}
    code = cur.get("weather_code", 0)
    condition = _code_to_condition(code)

    return {
        "ok": True,
        "location": {
            "name": r.get("name"),
            "admin1": r.get("admin1"),
            "country": r.get("country"),
            "lat": lat,
            "lon": lon,
        },
        "current": {
            "temp": cur.get("temperature_2m"),
            "wind": cur.get("wind_speed_10m"),
            "code": code,
            "condition": condition,
            "units": units,
        },
    }


def _code_to_condition(code: int) -> str:
    if code in (0,):
        return "clear"
    if code in (1, 2, 3):
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "unknown"
