import epd5in83_V2
from PIL import Image

epd = epd5in83_V2.EPD()
epd.init()

def display_image(image):
    epd.Clear()
    epd.display(epd.getbuffer(image))
    image.save("weather_station_display.png")
    image.show()
