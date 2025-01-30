import os
from PIL import Image

image_size = 24

def fetch_image(weather_condition):
    """Fetch weather icon image based on condition and return resized image."""
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script's directory
    icon_path = os.path.join(script_dir, "..", "icons", f"{weather_condition}.png")  # Correct relative path

    try:
        icon = Image.open(icon_path).resize((image_size, image_size)).convert('1')
        return icon
    except FileNotFoundError:
        print(f"Weather icon not found: {icon_path}. Skipping icon display.")
        return None
