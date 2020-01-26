#Imports
import time
from datetime import datetime

from termcolor import colored, cprint
import hashlib
import random
import math

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
accelOffsets = [0.0, 0.0, 0.0]

#======================================================================================================
#Initialize all hardware and check for OK
#Uses BCM numbering scheme, not BOARD
def initializeHardware(display_diagnostics = False, has_radio = False, ce_pin = board.D8, csn_pin = board.D17, has_accel = False, has_GPS = False, has_button = False, button_pin = 16):
    if has_radio:
        global address, spi, nrf
        try:
            address = b'1Node'
            ce = dio.DigitalInOut(ce_pin)
            csn = dio.DigitalInOut(csn_pin)
            spi = board.SPI()  # init spi bus object

            #Initialize the nRF24L01 on the spi bus object
            nrf = RF24(spi, csn, ce, ard=500, arc=15, data_rate=1, auto_ack = True)

            if display_diagnostics:
                nrf.what_happened(True)
            else:
                printOK("Radio Initialized")
        except:
            printCRIT("Radio required to proceed. Exiting.")
            quit()
    else:
        printCRIT("Radio required to proceed. Exiting.")
        quit()
        
    if has_accel:
        global mag, accel ,i2c
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            mag = adafruit_lsm303dlh_mag.LSM303DLH_Mag(i2c)
            accel = adafruit_lsm303_accel.LSM303_Accel(i2c)
            calibrateAccel(cycles = 50)
            printOK("Accel Initialized")
        except:
            printERR("Accel Error, Check Connections")
    else:
        printBYP("No Accel Installed... Bypassing")

    if has_GPS:
        global gps
        try:
            uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=10)
            gps = adafruit_gps.GPS(uart, debug=False)
            gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
            gps.send_command(b'PMTK220,1000')
            if display_diagnostics:
                gps.update()
                getGPSLock()
            else:
                printOK("GPS Initialized")
        except:
            printERROR("GPS Error, Check Connections")
    else:
        printBYP("No GPS Installed... Bypassing")
        
    if has_button:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(button_pin, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
        if display_diagnostics:
            print(interupt())
        else:
            printOK("Button Initialized")
    else:
        printBYP("No Button Installed... Bypassing")
    printOK("System Ready")
    print("=" * 40)
#======================================================================================================
def printOK(s):
    cprint("[OK] " + s, 'green')
    
def printBYP(s):
    cprint("[BYP] " + s, 'cyan')
    
def printERR(s):
    cprint("[ERROR] " + s, 'red', attrs=['bold'])
    
def printWARN(s):
    cprint("[WARNING] " + s, 'yellow')
    
def printALERT(s):
    cprint("[ALERT] " + s, 'magenta')
    
def printCRIT(s):
    cprint("[CRITICAL] " + s, 'grey', 'on_red')
    
#======================================================================================================
#Does NOT account for gravity
#Orientation is not an issue
def calibrateAccel(cycles = 10):
    printWARN("Cailibrating Accel...")
    global accelOffsets
    for x in range(cycles + 1):
        #first call is always 0, so skip
        if(x != 0):
            accelOffsets = [a+b for a,b in zip(getAccelReadings(calibrating = True), accelOffsets)]
    accelOffsets = [round(x/cycles,4) for x in accelOffsets]
    printALERT("Calibration Complete: "+ str(accelOffsets))
        
#If calibrating return raw measuremnt, else apply offsets
def getAccelReadings(calibrating = False):
    global accelOffsets
    if calibrating:
        return accel.acceleration
    else:
        return [round(a-b,4) for a,b in zip(accel.acceleration, accelOffsets)]
      
def getAccelVectorMag():
    return round(math.sqrt(sum([x**2 for x in getAccelReadings()])),4)
#======================================================================================================
      
def getGPSLock():
    location = ['Lat', None, 'Long', None, 'Quality', None, 'Alt', None, 'Speed', None, 'Angle', None]
    try:
        gps.update()
        if not gps.has_fix:
            # Try again if we don't have a fix yet.
            printALERT('Waiting for fix...')
            return location
        else:
            printOK('Lock Acquired')
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
    except:
        return location
#======================================================================================================

#Add 'BEGIN' and 'END' to list about to be transformed into bytearray
def addBeginAndEndSeq(l):
    l.insert(0, 'BEGIN')
    l.append('END')
    return l

#From https://www.raspberrypi-spy.co.uk/2012/06/finding-the-mac-address-of-a-raspberry-pi/
def getMAC(interface='wlan0'):
  # Return the MAC address of the specified interface
    try:
        str = open('/sys/class/net/%s/address' %interface).read()
    except:
        str = "00:00:00:00:00:00"
    return str[0:17]

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
    print("\nGenerated checksum: " + generated_hash)
    if (generated_hash == incoming_hash):
        return True
    else:
        return False

#Given a list, transform data into an array of bytes
def encodeDataIntoBytearray(l, encoding = 'utf_8'):
    buffer = []
    for s in l:
        buffer.append(bytes(str(s).encode(encoding)))
    return buffer

def decodeDataIntoList(l, encoding = 'utf_8'):
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
    address_data = ['MAC Addr', getMAC()]
    
    severity_data = ['Severity', severity]
    relay_data = ['Relay #', 0]
    
    final_data = generateSHA1Checksum(loc_data + date_ID_data + address_data+ severity_data + relay_data)
    return final_data

#UnPackage data for processing
def unpackageData(b):
    l = decodeDataIntoList(b)
    checksumValid = verifySHA1Checksum(l)
    if(checksumValid == False):
        printERR('Integrity FAIL')
    else:
        printOK('Integrity PASS')    
    
#======================================================================================================
#check if button (acting as an interupt has been pressed)
def interupt():
    return GPIO.input(button_GPIO_pin)

#======================================================================================================
#Transmission controller (Fire & Forget)
def transmissionControl():
    return

#Determine if given the data presented an alert should be sent/relayed
#Level 0, alert received, no data attached
#Level 1, alert received, time, ID, severity, and Relay
#Level 2, alert received, location, time, ID, severity, and Relay
#Level 3, alert received, location, speed, time, ID, severity, and Relay

#Returns play, bypass, or disregard
#This is where the magic happens
def determineAlertStatus():
    return

#======================================================================================================
#Once alert given, generate sound file to be played
def generateSoundFile():
    return

#play sound file
def playSoundFile():
    return

#======================================================================================================

initializeHardware(display_diagnostics = False, has_radio = True, has_accel = True, has_GPS = True, has_button = True, button_pin = button_GPIO_pin)
while True:
    getGPSLock()
    time.sleep(2)
