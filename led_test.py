import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
# GPIO.setmode(GPIO.BOARD)

BUTTON_PIN = 5  # example pin (BCM numbering)
BIN_BLUE = 17
STATUS_GREEN = 18

print("Waiting for touch-button press to toggle bin BLUE channel. CTRL+C to exit.")

def button_pressed(channel):
    # print("Button released!")
    GPIO.output(BIN_BLUE, not GPIO.input(BIN_BLUE))

GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BIN_BLUE, GPIO.OUT)
GPIO.setup(STATUS_GREEN, GPIO.OUT)

# Set up event detection (both edges or just falling/rising)
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_pressed, bouncetime=200)
# GPIO.add_event_detect(BUTTON_PIN, GPIO.RISING, callback=button_released, bouncetime=200)

try:
    while True:
        time.sleep(0.5)  # keep the program alive
        GPIO.output(STATUS_GREEN, not GPIO.input(STATUS_GREEN))
except KeyboardInterrupt:
    GPIO.cleanup()