import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(22, GPIO.IN)

while True:
    if GPIO.input(22) == 0:
        print("Not wet!\n")
        print(GPIO.input(22))
    else:
        print("WET!")
        print(GPIO.input(22))
    time.sleep(.5)
