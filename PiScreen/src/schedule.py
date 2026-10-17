"""Night mode: no API calls and no display updates between two times of day.

Configure with WEATHER_NIGHT="HH:MM-HH:MM" (default "00:00-06:00").
Use WEATHER_NIGHT=off to disable. Windows that cross midnight work too,
e.g. "23:00-06:00".
"""
import logging
import os
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
FOREVER = 10 ** 9  # "never" in seconds


def _parse(value):
    value = (value or "").strip().lower()
    if value in ("off", "none", "false", "0", ""):
        return None
    try:
        start, end = value.split("-")
        sh, sm = (int(p) for p in start.split(":"))
        eh, em = (int(p) for p in end.split(":"))
        if not (0 <= sh < 24 and 0 <= eh < 24 and 0 <= sm < 60 and 0 <= em < 60):
            raise ValueError
        if (sh, sm) == (eh, em):
            return None
        return (sh, sm), (eh, em)
    except ValueError:
        log.warning("Invalid WEATHER_NIGHT=%r, night mode disabled (use e.g. 00:00-06:00)", value)
        return None


WINDOW = _parse(os.environ.get("WEATHER_NIGHT", "00:00-06:00"))


def _minutes(t):
    return t[0] * 60 + t[1]


def is_night(now=None, window=None):
    window = window if window is not None else WINDOW
    if window is None:
        return False
    now = now or datetime.now()
    m = now.hour * 60 + now.minute
    start, end = _minutes(window[0]), _minutes(window[1])
    return start <= m < end if start < end else (m >= start or m < end)


def _seconds_until(now, hm):
    target = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def seconds_until_night_end(now=None, window=None):
    window = window if window is not None else WINDOW
    return 0 if window is None else _seconds_until(now or datetime.now(), window[1])


def seconds_until_night_start(now=None, window=None):
    window = window if window is not None else WINDOW
    return FOREVER if window is None else _seconds_until(now or datetime.now(), window[0])
