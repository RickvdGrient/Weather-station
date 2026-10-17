"""Thread-safe storage for the readings pushed by the external sensor."""
import threading
from datetime import datetime, timedelta

_lock = threading.Lock()
_reading = None  # (temperature, humidity, received_at)

MAX_AGE = timedelta(hours=1)

# Set whenever a new reading arrives so the refresh loop can react
changed = threading.Event()


def update(temperature, humidity):
    global _reading
    with _lock:
        _reading = (float(temperature), float(humidity), datetime.now())
    changed.set()


def latest():
    """Return (temperature, humidity) if the sensor reported recently, else None."""
    with _lock:
        if _reading is None:
            return None
        temperature, humidity, received = _reading
    if datetime.now() - received > MAX_AGE:
        return None
    return temperature, humidity
