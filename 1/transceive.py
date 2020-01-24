#Imports
import time
from datetime import datetime

import hashlib
import random

import board
import busio
import serial
import digitalio as dio
from circuitpython_nrf24l01 import RF24

import adafruit_lsm303_accel
import adafruit_lsm303dlh_mag

import adafruit_gps

import RPi.GPIO as GPIO

#Initialize all hardware and check for OK
#Uses BCM numbering scheme, not BOARD
def initializeHardware(display_diagnostics = False, has_radio = False, ce_pin = board.D8, csn_pin = board.D17, has_accel = False, has_GPS = False, has_button = False, button_pin = 16):
    if has_radio:
        global address, spi, nrf
        address = b'1Node'
        ce = dio.DigitalInOut(ce_pin)
        csn = dio.DigitalInOut(csn_pin)
        spi = board.SPI()  # init spi bus object

        #Initialize the nRF24L01 on the spi bus object
        nrf = RF24(spi, csn, ce, ard=500, arc=15, data_rate=1, auto_ack = True)

        if display_diagnostics:
            nrf.what_happened(True)
        else:
            print("Radio Initialized")
    else:
        print("No Radio Installed... Bypassing")
        
    if has_accel:
        global mag, accel ,i2c
        i2c = busio.I2C(board.SCL, board.SDA)
        mag = adafruit_lsm303dlh_mag.LSM303DLH_Mag(i2c)
        accel = adafruit_lsm303_accel.LSM303_Accel(i2c)
        print("Accel Initialized")
    else:
        print("No Accel Installed... Bypassing")

    if has_GPS:
        global gps
        uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=10)
        gps = adafruit_gps.GPS(uart, debug=False)
        gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
        gps.send_command(b'PMTK220,1000')
        if display_diagnostics:
            gps.update()
            getGPSLock()
        else:
            print("GPS Initialized")
    else:
        print("No GPS Installed... Bypassing")
        
    if has_button:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(button_pin, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
        if display_diagnostics:
            print(GPIO.input(button_pin))
        else:
            print("Button Initialized")
    else:
        print("No Button Installed... Bypassing")
        
def getGPSLock():
    location = [None] * 6
    gps.update()
    if not gps.has_fix:
        # Try again if we don't have a fix yet.
        print('Waiting for fix...')
        return location
    else:
        # We have a fix! (gps.has_fix is true)
        # Print out details about the fix like location, date, etc.
        location[0] = round(gps.latitude,6)
        location[1] = round(gps.longitude,6)
        location[2] = gps.fix_quality
        
        # Some attributes beyond latitude, longitude and timestamp are optional
        # and might not be present.  Check if they're None before trying to use!
        if gps.altitude_m is not None:
            location[3] = gps.altitude_m
        if gps.speed_knots is not None:
            location[4] = gps.speed_knots
        if gps.track_angle_deg is not None:
            location[5] = gps.track_angle_deg
        return location

            
initializeHardware(has_radio = True, has_accel = True, has_GPS = True, has_button = True)
while True:
    print(getGPSLock())

#Generate SHA-1 Checksum

#Verify SHA-1 Checksum transmitted vs. one generated from data received

#Package data from sensors (GPS, Accel for severity, Radio Info)
def packageData():
    return

#UnPackage data for processing
def unpackageData():
    return

#Transmission controller (Fire & Forget)

#Determine if given the data presented an alert should be sent/relayed

#Once alert given, generate sound file to be played

#play sound file