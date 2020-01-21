import RPi.GPIO as GPIO
from time import sleep
import Button

button = Button.TemporaryButton(36)

x = 0
while True:
    if button.getState() == GPIO.HIGH:
        print('Interupt Detected ' + str(x))
        x += 1
        sleep(.5)