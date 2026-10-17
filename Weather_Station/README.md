# E-ink weather station

Run from `PiScreen/src`:  `python3 index.py`

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `OPENWEATHER_API_KEY` | – | API key (or put it in `PiScreen/api_key.txt`) |
| `WEATHER_LANG` | `en` | `nl` = Dutch labels and descriptions |
| `WEATHER_NIGHT` | `00:00-06:00` | Night mode window, no updates/API calls. `off` disables, `23:00-06:00` also works |
| `WEATHER_PARTIAL` | `1` | `0` disables partial refresh |
| `WEATHER_PARTIAL_IDLE` | `1200` | Seconds without a partial refresh before the panel is put to sleep |
| `WEATHER_MAX_PARTIALS` | `20` | Max partial refreshes between two full refreshes (ghosting) |
| `WEATHER_CLEAR` | `1` | `0` skips the white flash before a full refresh |
| `WEATHER_HOST` | `0.0.0.0` | Address Flask listens on |
| `WEATHER_LAT` / `WEATHER_LON` | Oss | Location |

## How refreshing works

* Full refresh every hour (every 5 min while offline), and right when night mode ends.
* When the sensor posts a new reading to `/update-sensor`, only the top-left block
  (temperature, humidity) is redrawn with a partial refresh, at most once a minute and only if
  the displayed value would change.
* Night mode: the panel is put to sleep and the screen keeps its last image.

## Display driver

`epd5in83_V2.py` is Waveshare's newer driver (it has `init_Part` / `display_Partial`);
the only change is `import epdconfig` instead of `from . import epdconfig`.
Your original is saved as `epd5in83_V2.py.orig`. To roll back, swap the files back, the code
then falls back automatically to full refreshes only.
