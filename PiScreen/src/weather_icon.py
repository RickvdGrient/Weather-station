import logging
from functools import lru_cache
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

ICON_DIR = Path(__file__).resolve().parent.parent / "icons"
image_size = 24


@lru_cache(maxsize=None)
def _load(name, size):
    return Image.open(ICON_DIR / f"{name}.png").resize((size, size)).convert("1")


def fetch_image(weather_condition, size=image_size):
    """Return the (cached) 1-bit icon for an OpenWeather icon code, or None."""
    for name in (weather_condition, "not_found"):
        try:
            return _load(name, size)
        except (FileNotFoundError, OSError):
            continue
    log.warning("No icon found for %r and no not_found.png", weather_condition)
    return None
