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

button_GPIO_pin = 16

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
            print(interupt())
        else:
            print("Button Initialized")
    else:
        print("No Button Installed... Bypassing")
        
def getGPSLock():
    location = ['Lat', None, 'Long', None, 'Quality', None, 'Alt', None, 'Speed', None, 'Angle', None]
    gps.update()
    if not gps.has_fix:
        # Try again if we don't have a fix yet.
        print('Waiting for fix...')
        return location
    else:
        print('Lock Acquired')
        # We have a fix! (gps.has_fix is true)
        # Print out details about the fix like location, date, etc.
        location[1] = round(gps.latitude,6)
        location[3] = round(gps.longitude,6)
        location[5] = gps.fix_quality
        
        # Some attributes beyond latitude, longitude and timestamp are optional
        # and might not be present.  Check if they're None before trying to use!
        if gps.altitude_m is not None:
            location[7] = gps.altitude_m
        if gps.speed_knots is not None:
            location[9] = gps.speed_knots
        if gps.track_angle_deg is not None:
            location[11] = gps.track_angle_deg
        return location

#Add 'BEGIN' and 'END' to list about to be transformed into bytearray
def addBeginAndEndSeq(l):
    l.insert(0, 'BEGIN')
    l.append('END')
    return l

#Generate SHA-1 Checksum
def generateSHA1Checksum(l, len = 30, encoding = 'ASCII'):
    h = hashlib.new('sha1')
    v = ''
    
    #Add each value in l in string form
    for s in l:
        v = v +str(s)
    
    #Put into bytes for hashing
    h.update(bytes(v.encode(encoding)))
    
    #Append checksum to li
    l.append('Checksum')
    l.append(h.hexdigest()[0:len])
    l = addBeginAndEndSeq(l)
    return l

#Verify SHA-1 Checksum transmitted vs. one generated from data received
def verifySHA1Checksum(l, encoding = 'ASCII'):
    h = hashlib.new('sha1')
    v = ''
    
    #Add each value in l in string form without START, END, and CHECKSUM
    for s in l[1:-3]:
        v = v +str(s)
        
    #Decode data
    h.update(bytes(v.encode(encoding)))
    incoming_hash = l[l.index('Checksum')+1]
                      
    hash_len = len(incoming_hash)
    generated_hash = h.hexdigest()[0:hash_len]
    print("\nGenerated hash: " + generated_hash)
    if (generated_hash == incoming_hash):
        return True
    else:
        return False

#Given a list, transform data into an array of bytes
def encodeDataIntoBytearray(l, encoding = 'ASCII'):
    buffer = []
    for s in l:
        buffer.append(bytes(str(s).encode(encoding)))
    return buffer

def decodeDataIntoList(l, encoding = 'ASCII'):
    buffer = []
    for s in l:
        buffer.append(s.decode(encoding))
    return buffer

#Package data from sensors (GPS, Accel for severity, Radio Info)
#returns list of data in string form with checksum and Start & End seq
def packageData(severity=1):
    final_data = []
    loc_data = getGPSLock()
    
    ID = str(random.randint(0,9999999))
    date_ID_data = ['Date & ID #', str(datetime.now())[0:22] + " " + ID]
    
    severity_data = ['Severity', severity]
    relay_data = ['Relay #', 0]
    
    final_data = generateSHA1Checksum(loc_data + date_ID_data + severity_data + relay_data)
    return final_data

#UnPackage data for processing
def unpackageData(b):
    l = decodeDataIntoList(b)
    checksumValid = verifySHA1Checksum(l)
    if(checksumValid == False):
        return 'Integrity FAIL'
    else:
        return 'Integrity OK'

#check if button (acting as an interupt has been pressed)
def interupt():
    return GPIO.input(button_GPIO_pin)

#Transmission controller (Fire & Forget)
def transmissionControl():
    return

#Determine if given the data presented an alert should be sent/relayed
#Level 0, alert received, no data attached
#Level 1, alert received, time, ID, severity, and Relay
#Level 2, alert received, location, time, ID, severity, and Relay
#Level 3, alert received, location, speed, time, ID, severity, and Relay
def determineAlertStatus():
    return

#Once alert given, generate sound file to be played
def generateSoundFile():
    return

#play sound file
def playSoundFile():
    return

initializeHardware(display_diagnostics = False, has_radio = True, has_accel = True, has_GPS = True, has_button = True, button_pin = button_GPIO_pin)
v = packageData()
print(v)
x = encodeDataIntoBytearray(v)
print(x)
y = decodeDataIntoList(x)
print(y)
print(unpackageData(x))