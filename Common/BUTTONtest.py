import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)
GPIO.setup(36, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

x = 0
while True:
    if GPIO.input(36) == GPIO.HIGH:
        print('Interupt Detected ' + str(x))
        x += 1
        sleep(.5)