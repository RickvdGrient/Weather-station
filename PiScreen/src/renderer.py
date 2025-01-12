from PIL import Image, ImageDraw, ImageFont
import e_ink, api
from datetime import datetime, timedelta
import json

# Set up the display resolution
width, height, offset = 648, 480, 40
image_size = 64

temperature = 99
humidity = 99
received_temp_time = datetime.now()

font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 48)
font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
# font_large = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 48)
# font_medium = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 24)
# font_small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)


def render_image():
    image = Image.new('1', (width, height), 255)
    draw = ImageDraw.Draw(image)
    forecast_renderer(draw)

    try:
        icon = Image.open("../icons/cloudy.png").resize((image_size, image_size)).convert('1')  # Resize and convert to 1-bit color
        image.paste(icon, (5, 5))
    except FileNotFoundError:
        print("Weather icon not found. Skipping icon display.")

    e_ink.display_image(image)


def forecast_renderer(draw):
    forecast_data = api.request_weather_forecast()

    draw_current_weather(draw, forecast_data)
    draw_hourly_forecast(draw, forecast_data)
    draw_5_day_forecast(draw, forecast_data)


def draw_current_weather(draw, forecast_data):
    if current_weather_recent(received_temp_time) == False:
        global temperature 
        temperature = forecast_data["current"]["temp"]
        global humidity
        humidity = forecast_data["current"]["humidity"]

    temperature = round(temperature, 1)
    draw.text((image_size, 10), f"{temperature}°C", font=font_large, fill=0)
    draw.text((image_size, 100), f"{humidity}%", font=font_medium, fill=0)

    # draw.rectangle((width / 2 + 5, height / 2, width - 5 , height - 5 ), outline=0, width=2)
    # draw.rectangle((5, height / 2, width / 2 - 5, height - 5), outline=0, width=2)


def draw_5_day_forecast(draw, forecast_data):
    # Area for the 5-day forecast (top-right corner)
    forecast_width = width // 2
    forecast_height = height // 4
    start_x = width - forecast_width - offset
    start_y = offset
    limit_days = 5

    # Render up to 5 days of forecast in the top-right corner
    for i, data_point in enumerate(forecast_data["daily"][:limit_days]):
        timestamp = datetime.fromtimestamp(data_point["dt"])

        # Build the temperature range string
        temp_min = round(data_point["temp"]["min"])
        temp_max = round(data_point["temp"]["max"])
        day_temp_range = f"{temp_max}°C / {temp_min}°C"

        # Get the day of the week and day of the month
        day_of_week = timestamp.strftime("%a")  # Abbreviated day of the week (Mon, Tue, etc.)
        day_of_month = timestamp.strftime('%d')  # Day of the month (e.g., 8, 9, etc.)
        day_label = f"{day_of_week} {day_of_month}"

        # Render the day label and temperature range
        draw.text((start_x - 50, start_y + i * 30), f"{day_label}", font=font_small, fill=0)
        draw.text((start_x + 50, start_y + i * 30), f"{day_temp_range}", font=font_small, fill=0)

        # Fetch the description of the first forecast entry for that day
        description = data_point["weather"][0]["description"]
        draw.text((start_x + 160, start_y + i * 30), f"{description}", font=font_small, fill=0)


def draw_hourly_forecast(draw, forecast_data):
    graph_height = height // 1.5
    graph_width = width - offset
    max_points = 10
    step_x = graph_width / max_points - 1  # Space between points (12 points = 11 intervals)

    # Extract temperatures and timestamps
    temperatures = [round(hour["temp"]) for hour in forecast_data["hourly"][1::2][:max_points]]  # Round temperature values
    timestamps = []
    for hour in forecast_data["hourly"][1::2][:max_points]:
        timestamps.append(datetime.fromtimestamp(hour["dt"]).strftime("%H:%M"))

    # Normalize temperatures for graph scaling
    temp_min = min(temperatures) - 2  # Add some padding for better visualization
    temp_max = max(temperatures) + 2
    normalize = lambda temp: height - int(
        ((temp - temp_min) / (temp_max - temp_min)) * graph_height
    )

    # Draw graph lines and labels
    for i, temp in enumerate(temperatures):
        x = offset + i * step_x
        y = normalize(temp)

        # Draw temperature point
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=0)  # Circle at data point

        # Draw timestamp below
        draw.text((x - 15, height - 30), timestamps[i], font=font_small, fill=0)

        # Draw temperature above
        draw.text((x - 10, y - 20), f"{temp}°C", font=font_small, fill=0)

        # Draw connecting line to the next point (if not the last point)
        if i < len(temperatures) - 1:
            next_x = offset + (i + 1) * step_x
            next_y = normalize(temperatures[i + 1])
            draw.line((x, y, next_x, next_y), fill=0, width=1)


def current_weather_recent(prev_time):
    return prev_time > datetime.now() - timedelta(hours=1)

# render_image()
