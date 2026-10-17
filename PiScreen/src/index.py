import logging
import os
import threading
import time

from flask import Flask, jsonify, request

import e_ink
import renderer
import schedule
import sensor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("weather")

app = Flask(__name__)

REFRESH_OK = 3600              # seconds between full refreshes when everything works
REFRESH_RETRY = 300            # retry sooner when we're offline (e.g. wifi not up yet at boot)
PARTIAL_MIN_INTERVAL = 60      # at most one partial refresh per minute
IDLE_CHECK = 30                # how often the loop wakes up to check the idle timeout
FULL_GUARD = 5                 # skip a partial refresh if a full one is due within this many seconds

stop = threading.Event()


@app.route("/")
def hello():
    return "Weather station is running"


@app.route("/update-sensor", methods=["GET"])
def update_sensor():
    try:
        sensor.update(request.args["temperature"], request.args["humidity"])
    except (KeyError, ValueError):
        return jsonify({"status": 400, "error": "temperature and humidity must be numbers"}), 400
    return jsonify({"status": 200})


def refresh_loop():
    drawn_once = False     # always draw one frame after boot, even at night
    next_full = 0.0
    last_partial = 0.0

    while not stop.is_set():
        try:
            # ---- night mode: sleep the panel, do nothing until the night is over
            if drawn_once and schedule.is_night():
                wake = schedule.seconds_until_night_end()
                log.info("Night mode: pausing for %.0f minutes", wake / 60)
                e_ink.sleep()
                sensor.changed.clear()
                stop.wait(wake + 1)
                next_full = 0.0     # refresh right when the night ends
                continue

            # ---- full refresh
            if time.time() >= next_full:
                ok = renderer.render_image()
                drawn_once = True
                next_full = time.time() + (REFRESH_OK if ok else REFRESH_RETRY)
                last_partial = time.time()

            # ---- wait for the next thing to do (sensor update, full refresh, night, idle check)
            timeout = min(
                next_full - time.time(),
                schedule.seconds_until_night_start(),
                IDLE_CHECK,
            )
            if sensor.changed.wait(max(timeout, 0)):
                sensor.changed.clear()
                # rate limit; new readings arriving meanwhile are coalesced
                pause = PARTIAL_MIN_INTERVAL - (time.time() - last_partial)
                if pause > 0:
                    stop.wait(pause)
                if time.time() < next_full - FULL_GUARD and not schedule.is_night():
                    if renderer.partial_update():
                        last_partial = time.time()
            e_ink.sleep_if_idle()
        except Exception:  # keep the thread alive no matter what
            log.exception("Refresh loop error")
            stop.wait(REFRESH_RETRY)


def start_refresh_loop():
    threading.Thread(target=refresh_loop, daemon=True, name="refresh").start()


if __name__ == "__main__":
    start_refresh_loop()
    # Set WEATHER_HOST to your Pi's IP to bind to a single interface
    app.run(host=os.environ.get("WEATHER_HOST", "0.0.0.0"), port=5000, debug=False)
