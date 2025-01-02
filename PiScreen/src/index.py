from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
import renderer

app = Flask(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(renderer.render_image, 'interval', hours=1)
scheduler.start()

@app.route("/")
def hello():
	print("Hello World")
	return "Hello World"

@app.route("/update-sensor", methods=['GET'])
def get_temperature():
	renderer.temperature = request.args.get('temperature')
	renderer.humidity = request.args.get('humidity')
	renderer.received_temp_time = datetime.now()
	
	return jsonify({ "status": 200})

if __name__ == "__main__":
	renderer.render_image()
	app.run(host='192.168.50.69', port=5000, debug=False)
