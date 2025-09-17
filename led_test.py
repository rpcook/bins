import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
# GPIO.setmode(GPIO.BOARD)

GPIO.setup(9, GPIO.OUT)

for i in range(5):
    GPIO.output(9, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(9, GPIO.LOW)
    time.sleep(0.5)

GPIO.cleanup()