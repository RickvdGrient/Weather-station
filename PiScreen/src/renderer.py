import logging
import os
import threading
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

import api
import e_ink
import sensor
import weather_icon

log = logging.getLogger(__name__)

# Display resolution
width, height = 648, 480

# Layout (all in pixels)
MARGIN = 20
RIGHT_COL_X = 424          # 5-day forecast column
DIVIDER_Y = 212            # line between the top block and the hourly chart
CHART_X0, CHART_X1 = 44, 604
TEMP_TOP, TEMP_BOTTOM = 245, 370   # vertical range of the temperature line
RAIN_BASE, RAIN_MAX = 424, 36      # baseline and max height of the rain bars

LANG = os.environ.get("WEATHER_LANG", "en")
TEXT = {
    "en": {"today": "Today", "feels": "Feels like", "wind": "Wind", "humidity": "Humidity",
           "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
           "offline": "Offline - last update", "updated": "Updated"},
    "nl": {"today": "Vandaag", "feels": "Voelt als", "wind": "Wind", "humidity": "Vocht",
           "days": ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"],
           "offline": "Offline - laatste update", "updated": "Bijgewerkt"},
}.get(LANG, None) or {}
if not TEXT:
    LANG = "en"
    TEXT = {"today": "Today", "feels": "Feels like", "wind": "Wind", "humidity": "Humidity",
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "offline": "Offline - last update", "updated": "Updated"}

_render_lock = threading.Lock()  # never draw two frames at once

# Partial refresh: after this many partial updates wait for the next full refresh
# (partial updates build up ghosting; the hourly full refresh clears it)
MAX_PARTIALS = int(os.environ.get("WEATHER_MAX_PARTIALS", 20))
LEFT_BLOCK = (0, 0, RIGHT_COL_X - 16, DIVIDER_Y - 2)  # area that shows live sensor data

_state = {"image": None, "forecast": None, "shown": None, "partials": 0}


def _font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


font_extra_large = _font(64)
font_medium = _font(24)
font_small = _font(18)
font_tiny = _font(14)


# ---------------------------------------------------------------- main entry

def render_image():
    """Fetch data, draw one frame and push it to the display. Never raises."""
    with _render_lock:
        image = Image.new("1", (width, height), 255)
        draw = ImageDraw.Draw(image)
        ok = False
        forecast = shown = None

        try:
            forecast = api.get_forecast()
        except api.WeatherUnavailable as e:
            log.error("No weather data available: %s", e)
            draw_error(draw, "No internet", "No recent weather data available")
        except Exception:
            log.exception("Unexpected error while fetching the forecast")
            draw_error(draw, "Error", "Unexpected error, see the log")
        else:
            ok = not forecast.stale
            data = forecast.data
            draw.line((RIGHT_COL_X - 12, 12, RIGHT_COL_X - 12, DIVIDER_Y - 14), fill=0)
            draw.line((MARGIN, DIVIDER_Y, width - MARGIN, DIVIDER_Y), fill=0)
            shown = _safely(draw_current_weather, image, draw, data, forecast)
            _safely(draw_5_day_forecast, image, draw, _upcoming(data.get("daily", []), forecast.stale, 12 * 3600))
            _safely(draw_hourly_forecast, draw, _upcoming(data.get("hourly", []), forecast.stale, 3600))

        try:
            e_ink.display_image(image)
        except Exception:
            log.exception("Could not display the image")

        _state.update(
            image=image,
            forecast=forecast if forecast is not None and not forecast.stale else None,
            shown=shown, partials=0,
        )
        return ok


def partial_update():
    """Redraw the live (sensor) block if its values changed. Returns True if shown."""
    with _render_lock:
        forecast, shown = _state["forecast"], _state["shown"]
        if forecast is None or shown is None or _state["image"] is None:
            return False  # nothing drawn yet, or we are showing offline/cached data
        if _state["partials"] >= MAX_PARTIALS:
            return False
        reading = sensor.latest()
        if reading is None:
            return False
        if round(reading[0], 1) == shown[0] and round(reading[1]) == shown[1]:
            return False  # nothing visible would change

        image = _state["image"].copy()
        draw = ImageDraw.Draw(image)
        draw.rectangle(LEFT_BLOCK, fill=255)
        new_shown = _safely(draw_current_weather, image, draw, forecast.data, forecast)
        if new_shown is None:
            return False
        if not e_ink.display_partial(image):
            return False
        _state.update(image=image, shown=new_shown, partials=_state["partials"] + 1)
        log.info("Partial refresh %d/%d: %s", _state["partials"], MAX_PARTIALS, new_shown)
        return True


def _safely(fn, *args):
    """Run one drawing step; a bad field in one section must not blank the rest."""
    try:
        return fn(*args)
    except Exception:
        log.exception("Failed to draw %s", fn.__name__)
        return None


def _upcoming(entries, stale, grace):
    """Drop entries that are already in the past (only matters for cached data)."""
    if not stale:
        return entries
    cutoff = time.time() - grace
    return [e for e in entries if e["dt"] > cutoff]


def _hm(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def _centered(draw, x, y, text, font):
    """Draw text centered on x, clamped so it never leaves the screen."""
    w = draw.textlength(text, font=font)
    draw.text((min(max(x - w / 2, 2), width - w - 2), y), text, font=font, fill=0)


# ------------------------------------------------------------------- sections

def draw_error(draw, title, detail):
    draw.text((MARGIN * 2, 40), title, font=font_extra_large, fill=0)
    draw.text((MARGIN * 2, 130), detail, font=font_medium, fill=0)
    draw.text((MARGIN * 2, 170), datetime.now().strftime("Tried at %H:%M"), font=font_small, fill=0)


def draw_current_weather(image, draw, data, forecast):
    current = data["current"]

    # Prefer the local sensor when it reported within the last hour
    reading = sensor.latest()
    temperature = reading[0] if reading else float(current["temp"])
    humidity = reading[1] if reading else current.get("humidity")

    icon = weather_icon.fetch_image(current["weather"][0]["icon"], size=72)
    if icon:
        image.paste(icon, (MARGIN, 8))
    draw.text((MARGIN + 84, 4), f"{round(temperature, 1)}°C", font=font_extra_large, fill=0)

    description = current["weather"][0].get("description", "").capitalize()
    draw.text((MARGIN, 80), description, font=font_medium, fill=0)

    # Detail lines (every field is optional so a missing one just disappears)
    lines = []
    parts = []
    if "feels_like" in current:
        parts.append(f"{TEXT['feels']} {round(current['feels_like'])}°C")
    if "wind_speed" in current:
        parts.append(f"{TEXT['wind']} {round(current['wind_speed'] * 3.6)} km/h")
    lines.append("   ".join(parts))
    if humidity is not None:
        lines.append(f"{TEXT['humidity']} {round(float(humidity))}%")
    if "sunrise" in current and "sunset" in current:
        lines.append(f"↑ {_hm(current['sunrise'])}   ↓ {_hm(current['sunset'])}")

    y = 112
    for line in filter(None, lines):
        draw.text((MARGIN, y), line, font=font_small, fill=0)
        y += 24

    if forecast.stale:
        note = f"{TEXT['offline']} {datetime.fromtimestamp(forecast.fetched_at).strftime('%d %b %H:%M')}"
    else:
        note = f"{TEXT['updated']} {datetime.fromtimestamp(forecast.fetched_at).strftime('%H:%M')}"
    draw.text((MARGIN, DIVIDER_Y - 20), note, font=font_tiny, fill=0)

    return (round(temperature, 1), round(float(humidity)) if humidity is not None else None)


def draw_5_day_forecast(image, draw, days):
    row_h, start_y = 38, 12
    today = datetime.now().date()

    for i, day in enumerate(days[:5]):
        stamp = datetime.fromtimestamp(day["dt"])
        y = start_y + i * row_h
        label = TEXT["today"] if stamp.date() == today else f"{TEXT['days'][stamp.weekday()]} {stamp.day}"
        hi, lo = round(day["temp"]["max"]), round(day["temp"]["min"])

        draw.text((RIGHT_COL_X, y + 3), label, font=font_small, fill=0)
        icon = weather_icon.fetch_image(day["weather"][0]["icon"], size=28)
        if icon:
            image.paste(icon, (RIGHT_COL_X + 96, y))
        draw.text((RIGHT_COL_X + 130, y + 3), f"{hi}°/{lo}°", font=font_small, fill=0)


def draw_hourly_forecast(draw, hours):
    selected = hours[1::2][:8]  # every 2nd hour, next 16 hours
    if len(selected) < 2:
        return

    temps = [round(h["temp"]) for h in selected]
    lo, hi = min(temps) - 1, max(temps) + 1
    step = (CHART_X1 - CHART_X0) / (len(selected) - 1)

    def y_of(temp):
        return TEMP_BOTTOM - (temp - lo) / (hi - lo) * (TEMP_BOTTOM - TEMP_TOP)

    draw.line((MARGIN, RAIN_BASE, width - MARGIN, RAIN_BASE), fill=0)

    points = [(CHART_X0 + i * step, y_of(t)) for i, t in enumerate(temps)]
    draw.line(points, fill=0, width=2)

    for i, (hour, temp) in enumerate(zip(selected, temps)):
        x, y = points[i]
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=255, outline=0, width=2)
        _centered(draw, x, y - 27, f"{temp}°", font_small)

        # Rain chance: hatched bar growing up from the baseline
        pop = max(0.0, min(1.0, float(hour.get("pop", 0))))
        bar_h = round(pop * RAIN_MAX)
        if bar_h >= 2:
            left, right = x - 11, x + 11
            draw.rectangle((left, RAIN_BASE - bar_h, right, RAIN_BASE - 1), outline=0)
            for yy in range(RAIN_BASE - bar_h + 2, RAIN_BASE - 1, 3):
                draw.line((left + 1, yy, right - 1, yy), fill=0)

        _centered(draw, x, RAIN_BASE + 6, _hm(hour["dt"]), font_small)
        if pop >= 0.1:
            _centered(draw, x, RAIN_BASE + 28, f"{round(pop * 100)}%", font_tiny)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    render_image()
