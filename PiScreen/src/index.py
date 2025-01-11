from flask import Flask, jsonify, request
import renderer
import sys

app = Flask(__name__)

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

def call_renderer():
	renderer.render_image()

if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] == "run":
		call_renderer()

	app.run(host='192.168.50.69', port=5000, debug=False)
