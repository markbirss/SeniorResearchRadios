#Imports
import time
from datetime import datetime

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
            nrf = RF24(spi, csn, ce, ard=1000, arc=15, data_rate=1, auto_ack = True)

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
            gps.send_command(b'PMTK220,200')
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
    print("\033[0;32m[OK] " + s + '\033[2J')
    
def printBYP(s):
    print("\033[0;36m[BYP] " + s + '\033[2J')
    
def printDIAG(s):
    print("\033[0;34m[DIAG] " + s + '\033[2J')
    
def printERR(s):
    print("\033[1;31m[ERROR] " + s + '\033[2J')
    
def printWARN(s):
    print("\033[1;33m[WARNING] " + s + '\033[2J')
    
def printALERT(s):
    print("\033[1;35m[ALERT] " + s + '\033[2J')
    
def printCRIT(s):
    print("\033[1;30;41m[CRITICAL] " + s + '\033[2J')
    
#======================================================================================================
#Does NOT account for gravity
#Orientation is not an issue
def calibrateAccel(cycles = 10):
    printWARN("Calibrating Accel...")
    global accelOffsets
    for x in range(cycles + 1):
        #first call is always 0, so skip
        if(x != 0):
            accelOffsets = [a+b for a,b in zip(getAccelReadings(calibrating = True), accelOffsets)]
        time.sleep(0.05)    
    accelOffsets = [round(x/cycles,4) for x in accelOffsets]
    printDIAG("Calibration Complete: "+ str(accelOffsets))
        
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
    location = ['Lat', None, 'Long', None, 'Satellites', None, 'Alt', None, 'Speed', None, 'Angle', None]
    gps.update()
    if not gps.has_fix:
        # Try again if we don't have a fix yet.
        printALERT('No Lock')
        return location
    else:
        printOK('Lock Acquired')
        # We have a fix! (gps.has_fix is true)
        # Print out details about the fix like location, date, etc.
        location[1] = round(gps.latitude,6)
        location[3] = round(gps.longitude,6)
        location[5] = gps.satellites
            
        # Some attributes beyond latitude, longitude and timestamp are optional
        # and might not be present.  Check if they're None before trying to use!
        if gps.altitude_m is not None:
            location[7] = gps.altitude_m
        if gps.speed_knots is not None:
            location[9] = gps.speed_knots
        if gps.track_angle_deg is not None:
            location[11] = gps.track_angle_deg
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
    
    #Find last occurance of Begin before end in list
    end_index = next(i for i in reversed(range(len(l))) if l[i] == 'END')
    end_index += 1
    l = l[0:end_index]
    
    begin_index = next(i for i in reversed(range(len(l))) if l[i] == 'BEGIN')
    l = l[begin_index:]
    
    checksumValid = verifySHA1Checksum(l)
    if(checksumValid == False):
        printERR('Integrity FAIL')
    else:
        printOK('Integrity PASS')
    return l
    
#======================================================================================================
#check if button (acting as an interupt has been pressed)
def interupt():
    return GPIO.input(button_GPIO_pin)

#======================================================================================================
#Transmission controller (Fire & Forget)
def transmissionControl(sensitivity = 10):
    printALERT("Beginning Transmission Controller")
    nrf.open_rx_pipe(0, address)
    nrf.listen = True
    
    #While not interupt sequence (i.e. forever)
    timeout = 60
    
    begin = time.monotonic()  # start timer
    last_print_idle = begin
    
    while time.monotonic() < begin + timeout:
        now = time.monotonic()
    
        #Check accelerometer for crash-level movement
        if getAccelVectorMag() > sensitivity:
            nrf.listen = False
            printALERT("Incident Detected")
            print("=" * 40)
            #Channel clear
            
            #Bundle data
            l = packageData()
            
            x = 0
            while x < 3:
                result = nrf.send(l)
                if r.contains(False):
                    x +=1
                else:
                    break
            printALERT("Transmission Sent")
            
            #Wait for ack

            #All clear
        
            #End and return to normal operation with timeout to next alert so same event does not trigger multiple events
            print("=" * 40)
            
        #Has ANY data been received?
        elif nrf.any():
            print("=" * 40)
            printALERT("Alert Received")
            printDIAG("Logging Alert")
            
            msg = []
            rec = now
            while abs(rec - now) < 2:
                now = time.monotonic()
                if nrf.any():
                    msg.append(nrf.recv())
            data = unpackageData(msg)
            print(data)
            #If one received ,log details

            #Determien severity
            alert = determineAlertStatus()
            if alert == 'Play Alert':
                filename = generateSoundFile()
                playSoundFile(filename)
            print("=" * 40)
        
        elif now - last_print_idle > 5:
            last_print_idle = now
            printOK("Idle")
    nrf.listen = False

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
transmissionControl()
