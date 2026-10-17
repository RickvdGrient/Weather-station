import logging
import os
import time

import e_ink
import renderer
import schedule

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("weather")

REFRESH_OK = 3600      # seconds between full refreshes when everything works
REFRESH_RETRY = 300    # retry sooner when we're offline (e.g. wifi not up yet at boot)
PARTIAL_INTERVAL = int(os.environ.get("WEATHER_PARTIAL_INTERVAL", 900))  # fresh data + partial refresh
FULL_GUARD = 60        # skip a partial refresh if a full one is due within this many seconds
MAX_SLEEP = 60         # wake up at least this often (idle-sleep check)


def main():
    drawn_once = False   # always draw one frame after boot, even at night
    next_full = 0.0
    next_partial = float("inf")

    while True:
        try:
            # Night mode: sleep the panel, do nothing until the night is over
            if drawn_once and schedule.is_night():
                wake = schedule.seconds_until_night_end()
                log.info("Night mode: pausing for %.0f minutes", wake / 60)
                e_ink.sleep()
                time.sleep(wake + 1)
                next_full = 0.0    # refresh right when the night ends
                continue

            now = time.time()
            if now >= next_full:
                ok = renderer.render_image()
                drawn_once = True
                next_full = time.time() + (REFRESH_OK if ok else REFRESH_RETRY)
                next_partial = time.time() + PARTIAL_INTERVAL if e_ink.supports_partial() else float("inf")
            elif now >= next_partial:
                if next_full - now > FULL_GUARD:
                    renderer.partial_update()
                next_partial = time.time() + PARTIAL_INTERVAL

            e_ink.sleep_if_idle()
            nap = min(next_full, next_partial, time.time() + schedule.seconds_until_night_start()) - time.time()
            time.sleep(max(1.0, min(nap, MAX_SLEEP)))
        except Exception:  # keep running no matter what
            log.exception("Refresh loop error")
            time.sleep(REFRESH_RETRY)


if __name__ == "__main__":
    main()
