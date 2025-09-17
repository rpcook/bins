import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

BUTTON_PIN = 5  # example pin (BCM numbering)
BIN_BLUE = 17
STATUS_GREEN = 18

print("Waiting for touch-button press to toggle bin BLUE channel. CTRL+C to exit.")

def button_pressed(channel):
    GPIO.output(BIN_BLUE, not GPIO.input(BIN_BLUE))

GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BIN_BLUE, GPIO.OUT)
GPIO.setup(STATUS_GREEN, GPIO.OUT)

# Set up event detection (both edges or just falling/rising)
GPIO.add_event_detect(BUTTON_PIN, GPIO.RISING, callback=button_pressed, bouncetime=20)

try:
    while True:
        time.sleep(0.5)  # keep the program alive
        GPIO.output(STATUS_GREEN, not GPIO.input(STATUS_GREEN))
except KeyboardInterrupt:
    GPIO.cleanup()