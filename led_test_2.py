import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
# GPIO.setmode(GPIO.BOARD)

BUTTON_PIN = 5  # example pin (BCM numbering)

def button_pressed(channel):
    print("Button pressed!")

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set up event detection (both edges or just falling/rising)
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_pressed, bouncetime=200)

try:
    while True:
        time.sleep(1)  # keep the program alive
except KeyboardInterrupt:
    GPIO.cleanup()