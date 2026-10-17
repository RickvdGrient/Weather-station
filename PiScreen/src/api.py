"""OpenWeather One Call client with timeout, validation and an on-disk cache.

If the network (or the API) is unavailable, the last good forecast is
returned instead, flagged as stale, so the display never has to crash.
"""
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

log = logging.getLogger(__name__)

LATITUDE = float(os.environ.get("WEATHER_LAT", 51.76424342226612))
LONGITUDE = float(os.environ.get("WEATHER_LON", 5.5196964510068955))

BASE_DIR = Path(__file__).resolve().parent
CACHE_FILE = BASE_DIR / "forecast_cache.json"
KEY_FILE = BASE_DIR.parent / "api_key.txt"  # git-ignored fallback to the env var

TIMEOUT = (5, 15)           # (connect, read) seconds
MAX_CACHE_AGE = 12 * 3600   # don't show a forecast older than this
REQUIRED_KEYS = ("current", "hourly", "daily")


class WeatherUnavailable(Exception):
    """No fresh data and no usable cache."""


@dataclass
class Forecast:
    data: dict
    fetched_at: float   # unix time the data was downloaded
    stale: bool         # True if this came from the cache


def _api_key():
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    if not key:
        raise WeatherUnavailable(
            "No API key: set OPENWEATHER_API_KEY or create PiScreen/api_key.txt"
        )
    return key


def _download():
    params = {
        "lat": LATITUDE,
        "lon": LONGITUDE,
        "exclude": "minutely,alerts",
        "units": "metric",
        "lang": os.environ.get("WEATHER_LANG", "en"),  # "nl" gives Dutch descriptions
        "appid": _api_key(),
    }
    response = requests.get(
        "https://api.openweathermap.org/data/3.0/onecall", params=params, timeout=TIMEOUT
    )
    response.raise_for_status()
    data = response.json()
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"API response is missing {missing}: {str(data)[:200]}")
    return data


def _save_cache(data):
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"fetched_at": time.time(), "data": data}))
    tmp.replace(CACHE_FILE)  # atomic: a power cut can't leave a half-written file


def _load_cache():
    try:
        cached = json.loads(CACHE_FILE.read_text())
        age = time.time() - cached["fetched_at"]
        if age > MAX_CACHE_AGE:
            log.warning("Cached forecast is %.1f h old, ignoring it", age / 3600)
            return None
        if any(k not in cached["data"] for k in REQUIRED_KEYS):
            log.warning("Cached forecast is incomplete, ignoring it")
            return None
        return Forecast(cached["data"], cached["fetched_at"], stale=True)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def get_forecast(retries=3, delay=5):
    """Return a Forecast (fresh if possible, cached otherwise).

    Raises WeatherUnavailable only when there is neither.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            data = _download()
            try:
                _save_cache(data)
            except OSError as e:
                log.warning("Could not write forecast cache: %s", e)
            return Forecast(data, time.time(), stale=False)
        except WeatherUnavailable:
            raise  # missing key: retrying won't help
        except (requests.RequestException, ValueError) as e:
            last_error = e
            log.warning("Weather request failed (%d/%d): %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(delay)

    cached = _load_cache()
    if cached:
        return cached
    raise WeatherUnavailable(f"No connection and no usable cache ({last_error})")
