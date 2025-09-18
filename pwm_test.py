import RPi.GPIO as GPIO
import time
import threading

BUTTON_PIN = 5  # BCM numbering
DOUBLE_TAP_TIME = 0.3   # seconds
LONG_HOLD_TIME = 0.5    # seconds
BIN_RED = 10
BIN_GREEN = 9
BIN_BLUE = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN)
GPIO.setup(BIN_RED, GPIO.OUT)
GPIO.setup(BIN_GREEN, GPIO.OUT)
GPIO.setup(BIN_BLUE, GPIO.OUT)

r = GPIO.PWM(BIN_RED, 200)
g = GPIO.PWM(BIN_GREEN, 200)
b = GPIO.PWM(BIN_BLUE, 200)
r.start(0)
g.start(0)
b.start(0)

control_channel = (r, g, b)
current_channel = 0

last_press_time = 0
press_start_time = 0
single_timer = None

def handle_single():
    if not GPIO.input(BUTTON_PIN) == GPIO.HIGH: # if the button input is still high, do nothing
        print("Single press")
        # GPIO.output(BIN_RED, not GPIO.input(BIN_RED))

def handle_double():
    global current_channel
    print("Double tap")
    # GPIO.output(BIN_GREEN, not GPIO.input(BIN_GREEN))
    current_channel = (current_channel + 1) % 3
    r.ChangeDutyCycle(0)
    g.ChangeDutyCycle(0)
    b.ChangeDutyCycle(0)
    control_channel[current_channel].ChangeDutyCycle(100)
    # GPIO.output(BIN_RED, GPIO.LOW)
    # GPIO.output(BIN_GREEN, GPIO.LOW)
    # GPIO.output(BIN_BLUE, GPIO.LOW)
    # GPIO.output(control_channel[current_channel], GPIO.HIGH)

def handle_long():
    print("Long hold")
    # GPIO.output(BIN_BLUE, not GPIO.input(BIN_BLUE))

def button_pressed(channel):
    global last_press_time, press_start_time, single_timer
    press_time = time.monotonic()
    delta = press_time - last_press_time

    # log_event("PRESS")

    if delta < DOUBLE_TAP_TIME:
        if single_timer:
            single_timer.cancel()
        handle_double()
    else:
        press_start_time = press_time
        # schedule long-hold check
        threading.Timer(LONG_HOLD_TIME, check_hold, [press_time]).start()
        # schedule single-press detection unless another tap arrives
        single_timer = threading.Timer(DOUBLE_TAP_TIME, handle_single)
        single_timer.start()

    last_press_time = press_time

def button_released(channel):
    global press_start_time
    release_time = time.monotonic()
    # log_event("RELEASE")
    press_start_time = 0

def check_hold(start_time):
    # if button still held after LONG_HOLD_TIME, it's a long hold
    if GPIO.input(BUTTON_PIN) == GPIO.HIGH and press_start_time == start_time:
        if single_timer:
            single_timer.cancel()
        handle_long()

# Set up event detection for both edges
GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, bouncetime=10)

GPIO.add_event_callback(
    BUTTON_PIN,
    lambda ch: (
        button_pressed(ch) if GPIO.input(ch) == GPIO.HIGH else button_released(ch)
    )
)

print("Listening for button events... (CTRL+C to exit)")

try:
    while True:
        # for dc in range(0, 101, 5):
        #     g.ChangeDutyCycle(dc)
        #     time.sleep(0.2)
        # for dc in range(100, -1, -5):
        #     g.ChangeDutyCycle(dc)
        #     time.sleep(0.2)
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    r.stop()
    g.stop()
    b.stop()
    GPIO.cleanup()
