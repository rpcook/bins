import RPi.GPIO as GPIO
import time
import threading
import sys
import select

BUTTON_PIN = 5  # BCM numbering
DOUBLE_TAP_TIME = 0.3   # seconds
LONG_HOLD_TIME = 1.0    # seconds

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN)

last_press_time = 0
press_start_time = 0
single_timer = None
# event_log = []   # store (event_type, timestamp) tuples

def log_event(event_type):
    ts = time.monotonic()
    # event_log.append((event_type, ts))
    print(f"[{ts:.3f}] {event_type}")

def handle_single():
    log_event("Single press")

def handle_double():
    log_event("Double tap")

def handle_long():
    log_event("Long hold")

def button_pressed(channel):
    global last_press_time, press_start_time, single_timer
    press_time = time.monotonic()
    delta = press_time - last_press_time

    log_event("PRESS")

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
    log_event("RELEASE")
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

print("Listening for button events... (press any key to exit)")

try:
    while True:
        # Check if a key was pressed (non-blocking)
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            break
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    # print("\nEvent log dump:")
    # for event, ts in event_log:
    #     print(f"{ts:.3f}: {event}")
    GPIO.cleanup()
