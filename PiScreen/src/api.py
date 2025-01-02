import requests

api_key = "7c9df2a3a561369fbab15e741e18fb31"
latitude = 51.76424342226612
longitude = 5.5196964510068955

def request_weather_forecast():
    url = f'https://api.openweathermap.org/data/3.0/onecall?lat={latitude}&lon={longitude}&exclude=minutely,alerts&appid={api_key}&units=metric'
    response = requests.get(url)
    return response.json()
