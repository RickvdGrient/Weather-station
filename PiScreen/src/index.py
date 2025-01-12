from flask import Flask, jsonify, request
from datetime import datetime
import renderer
import threading
import time

app = Flask(__name__)

data_lock = threading.Lock()

@app.route("/")
def hello():
	print("Hello World")
	return "Hello World"

@app.route("/update-sensor", methods=['GET'])
def get_temperature():
	with data_lock:
		renderer.temperature = request.args.get('temperature')
		renderer.humidity = request.args.get('humidity')
		renderer.received_temp_time = datetime.now()
	
	return jsonify({ "status": 200})

def start_hourly_task():
    """Runs the run() function every hour in the same process."""
    def task():
        while True:
            renderer.render_image()
            time.sleep(3600)  # Wait for 1 hour before running again
    thread = threading.Thread(target=task, daemon=True)
    thread.start()


if __name__ == "__main__":
	start_hourly_task()

	app.run(host='192.168.50.69', port=5000, debug=False)
