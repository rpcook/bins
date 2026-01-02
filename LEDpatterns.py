import time

def solid_colour(led, RGB):
    while True:
        led._apply_rgb(RGB[0], RGB[1], RGB[2])
        time.sleep(0.1)
        yield

def next_bin(led, RGB, days):
    # assign the bin indicator next bin colour
    led._apply_rgb(RGB[0], RGB[1], RGB[2])
    time.sleep(2)
    yield
    for i in range(days):
        # flash the bin indicator to show how many days ahead
        led._apply_rgb(0, 0, 0)
        time.sleep(0.3)
        led._apply_rgb(RGB[0], RGB[1], RGB[2])
        time.sleep(0.3)
        yield
    led._apply_rgb(0, 0, 0)
    led.remove_job("user_request_next_bin")

def turn_off(led):
    while True:
        led._apply_rgb(0, 0, 0)
        time.sleep(0.1)
        yield

def heartbeat(led):
    led._apply_rgb(0,4,0)
    for i in range(2):
        time.sleep(0.05)
        yield
    led._apply_rgb(0,0,0)

def success(led):
    for i in range(3):
        led._apply_rgb(0,30,0)
        time.sleep(0.5)
        yield
        led._apply_rgb(0,0,0)
        time.sleep(0.5)
        yield
    led.remove_job("success")

def error(led):
    for i in range(3):
        led._apply_rgb(30,0,0)
        time.sleep(0.5)
        yield
        led._apply_rgb(0,0,0)
        time.sleep(0.5)
        yield
    led.remove_job("error")

def web_activity(led):
    while True:
        led._apply_rgb(0,0,10)
        time.sleep(0.05)
        led._apply_rgb(0,0,0)
        time.sleep(0.05)
        yield