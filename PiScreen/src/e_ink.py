"""Display output. Works without the panel too (it then only saves a PNG).

Full refresh:    init -> Clear -> display (flashes, removes ghosting).
Partial refresh: needs Waveshare's newer driver (init_Part/display_Partial).
                 The panel is kept awake after a full refresh so partial
                 updates can follow, and is put to sleep after
                 WEATHER_PARTIAL_IDLE seconds without activity, and at night.
Without the newer driver it falls back to "full refresh, then sleep".
"""
import logging
import os
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

OUTPUT_PNG = Path(__file__).resolve().parent / "weather_station_display.png"
PREVIEW = os.environ.get("WEATHER_PREVIEW") == "1"            # open the PNG on a desktop
PARTIAL_ENABLED = os.environ.get("WEATHER_PARTIAL", "1") == "1"
CLEAR_FIRST = os.environ.get("WEATHER_CLEAR", "1") == "1"      # extra white flash vs. less ghosting
IDLE_SLEEP = int(os.environ.get("WEATHER_PARTIAL_IDLE", 20 * 60))

try:
    import epd5in83_V2
except Exception as e:  # no SPI/GPIO libraries, e.g. on a dev laptop
    epd5in83_V2 = None
    log.warning("E-ink driver unavailable, saving PNG only: %s", e)

_lock = threading.RLock()
_epd = None
_awake = False          # panel powered and holding our last frame
_partial_mode = False   # init_Part() already called since the last full refresh
_last_activity = 0.0


def _get_epd():
    global _epd
    if _epd is None:
        _epd = epd5in83_V2.EPD()
    return _epd


def supports_partial():
    return (
        PARTIAL_ENABLED
        and epd5in83_V2 is not None
        and hasattr(epd5in83_V2.EPD, "init_Part")
        and hasattr(epd5in83_V2.EPD, "display_Partial")
    )


def _save_preview(image):
    try:
        image.save(OUTPUT_PNG)
    except OSError as e:
        log.warning("Could not save preview PNG: %s", e)
    if PREVIEW:
        image.show()


def display_image(image):
    """Full refresh."""
    global _awake, _partial_mode, _last_activity
    _save_preview(image)
    if epd5in83_V2 is None:
        return
    with _lock:
        try:
            epd = _get_epd()
            epd.init()
            if CLEAR_FIRST:
                epd.Clear()
            epd.display(epd.getbuffer(image))
            _awake, _partial_mode, _last_activity = True, False, time.time()
        except Exception:
            log.exception("Failed to update the e-ink display")
        finally:
            # Without partial support there is no reason to stay powered.
            if not supports_partial() or not _awake:
                _sleep_locked()


def display_partial(image):
    """Partial refresh of the whole frame. Returns True if it was shown."""
    global _partial_mode, _last_activity
    if not supports_partial():
        return False
    with _lock:
        if not _awake:
            return False  # panel slept; wait for the next full refresh
        _save_preview(image)
        try:
            epd = _get_epd()
            if not _partial_mode:
                epd.init_Part()
                _partial_mode = True
            epd.display_Partial(epd.getbuffer(image))
            _last_activity = time.time()
            return True
        except Exception:
            log.exception("Partial refresh failed")
            _sleep_locked()
            return False


def _sleep_locked():
    global _awake, _partial_mode
    if _epd is not None and _awake:
        try:
            _epd.sleep()
        except Exception:
            log.exception("Failed to put the e-ink display to sleep")
    _awake = _partial_mode = False


def sleep():
    with _lock:
        _sleep_locked()


def sleep_if_idle(max_idle=None):
    """Put the panel to sleep if nothing was drawn for a while."""
    max_idle = IDLE_SLEEP if max_idle is None else max_idle
    with _lock:
        if _awake and time.time() - _last_activity > max_idle:
            log.info("Display idle for %d s, sleeping", max_idle)
            _sleep_locked()
