import time

def solid_colour(led, RGB):
    while True:
        led._apply_rgb(RGB[0], RGB[1], RGB[2])
        time.sleep(0.1)
        yield

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

def web_activity(led):
    while True:
        led._apply_rgb(0,0,10)
        time.sleep(0.05)
        led._apply_rgb(0,0,0)
        time.sleep(0.05)
        yield

def success(led):
    for i in range(3):
        led._apply_rgb(0,30,0)
        time.sleep(0.5)
        yield
        led._apply_rgb(0,0,0)
        time.sleep(0.5)
        yield
    led.remove_job("success")    