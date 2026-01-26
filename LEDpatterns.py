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

def heartbeat(led, alertLevel):
    if alertLevel == 0:
        # no alert, briefly flash green
        led._apply_rgb(0,4,0)
        time.sleep(0.1)
    if alertLevel == 1:
        # recoverable issue, medium amber flash
        led._apply_rgb(4,2,0)
        time.sleep(0.3)
    if alertLevel == 2:
        # serious issue, long red flash
        led._apply_rgb(4,0,0)
        time.sleep(0.5)
    led._apply_rgb(0,0,0)
    led.remove_job("heartbeat")
    yield

def success(led, brightness=30):
    for i in range(3):
        led._apply_rgb(0,brightness,0)
        time.sleep(0.5)
        yield
        led._apply_rgb(0,0,0)
        time.sleep(0.5)
        yield
    led.remove_job("success")

def error(led, brightness=30):
    for i in range(3):
        led._apply_rgb(brightness,0,0)
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