import time

def solid_colour(led, RGB):
    while True:
        led._apply_rgb(RGB[0], RGB[1], RGB[2])
        time.sleep(0.1)
        yield