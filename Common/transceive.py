#Imports
import time
from datetime import datetime

import hashlib
import random
import math

import RPi.GPIO as GPIO
import board

import config as cfg

button_GPIO_pin = 16
accelOffsets = [0.0, 0.0, 0.0]

#======================================================================================================
#Initialize all hardware and check for OK
#Uses BCM numbering scheme, not BOARD
def initializeHardware(display_diagnostics = False, has_radio = False, ce_pin = board.D8, csn_pin = board.D17, has_accel = False, has_GPS = False, has_button = False, button_pin = 16, ch = 76):
    if has_radio:
        from circuitpython_nrf24l01 import RF24
        import digitalio as dio
        global address, spi, nrf
        try:
            address = b'1Node'
            ce = dio.DigitalInOut(ce_pin)
            csn = dio.DigitalInOut(csn_pin)
            spi = board.SPI()  # init spi bus object

            #Initialize the nRF24L01 on the spi bus object
            nrf = RF24(spi, csn, ce, ard=2000, arc=15, data_rate=1, auto_ack = True, channel = ch)

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
        import adafruit_lsm303_accel
        import adafruit_lsm303dlh_mag
        import busio
        global mag, accel ,i2c
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            mag = adafruit_lsm303dlh_mag.LSM303DLH_Mag(i2c)
            accel = adafruit_lsm303_accel.LSM303_Accel(i2c)
            calibrateAccel(cycles = 25)
            printOK("Accel Initialized")
        except:
            printERR("Accel Error, Check Connections")
    else:
        printBYP("No Accel Installed... Bypassing")

    if has_GPS:
        import serial
        import adafruit_gps
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
    print("\033[0;32m[OK] " + s + '\033[0;0m')
    
def printBYP(s):
    print("\033[0;36m[BYP] " + s + '\033[0;0m')
    
def printDIAG(s):
    print("\033[0;34m[DIAG] " + s + '\033[0;0m')
    
def printERR(s):
    print("\033[1;31m[ERROR] " + s + '\033[0;0m')
    
def printWARN(s):
    print("\033[1;33m[WARNING] " + s + '\033[0;0m')
    
def printALERT(s):
    print("\033[1;35m[ALERT] " + s + '\033[0;0m')
    
def printCRIT(s):
    print("\033[1;30;41m[CRITICAL] " + s + '\033[0;0m')
    
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
    if has_accel:
        return round(math.sqrt(sum([x**2 for x in getAccelReadings()])),4)
    else:
        return 0
#======================================================================================================
      
def getGPSLock(verbose = False):
    location = [None, None, None]
    if has_GPS:
        gps.update()
        if not gps.has_fix:
            # Try again if we don't have a fix yet.
            if verbose:
                printWARN('No Lock')
            return location
        else:
            if verbose:
                printOK('Lock Acquired')
            # We have a fix! (gps.has_fix is true)
            # Print out details about the fix like location, date, etc.
            location[0] = round(gps.latitude,6)
            location[1] = round(gps.longitude,6)
                
            # Some attributes beyond latitude, longitude and timestamp are optional
            # and might not be present.  Check if they're None before trying to use!
            if gps.speed_knots is not None:
                location[2] = gps.speed_knots
            return location
    else:
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
def generateSHA1Checksum(l, len = 20, encoding = 'utf_8'):
    h = hashlib.new('sha1')
    v = ''
    
    #Add each value in l in string form
    for s in l:
        v = v +str(s)
    
    #Put into bytes for hashing
    h.update(bytes(v.encode(encoding)))
    
    #Append checksum to li
    l.append(h.hexdigest()[0:len])
    l = addBeginAndEndSeq(l)
    return l

#Verify SHA-1 Checksum transmitted vs. one generated from data received
def verifySHA1Checksum(l, encoding = 'utf_8'):
    h = hashlib.new('sha1')
    v = ''
    
    #Add each value in l in string form without START, END, and CHECKSUM
    for s in l[1:-3]:
        v = v +str(s)
        
    #Decode data
    h.update(bytes(v.encode(encoding)))
    incoming_hash = l[l.index('END')-1]
                      
    hash_len = len(incoming_hash)
    generated_hash = h.hexdigest()[0:hash_len]
    printDIAG("Generated checksum: " + generated_hash)
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
    printDIAG("Gathering Data")
    final_data = []
    loc_data = getGPSLock(verbose = True)
    
    ID = str(random.randint(0,9999999))
    date_ID_data = [str(datetime.utcnow())[0:22] + " " + ID]
    address_data = [getMAC()]
    
    severity_data = [severity]
    relay_data = [0]
    
    final_data = generateSHA1Checksum(loc_data + date_ID_data + address_data+ severity_data + relay_data)
    final_data = encodeDataIntoBytearray(final_data)
    return final_data

#UnPackage data for processing
def unpackageData(b):
    l = decodeDataIntoList(b)
    
    #Find last occurance of Begin before end in list
    if 'END' in l:
        end_index = next(i for i in reversed(range(len(l))) if l[i] == 'END')
        end_index += 1
        l = l[0:end_index]
        if 'BEGIN' in l:
            begin_index = next(i for i in reversed(range(len(l))) if l[i] == 'BEGIN')
            l = l[begin_index:]
        else:
             printERR("No BEGIN/END Sequence Found")
             return [l, False]
    else:
        printERR("No BEGIN/END Sequence Found")
        return [l, False]
    
    checksumValid = verifySHA1Checksum(l)
    if(checksumValid == False):
        printERR('Integrity FAIL')
    else:
        printOK('Integrity PASS')
    return [l, checksumValid]
    
#======================================================================================================
#check if button (acting as an interupt has been pressed)
def interupt():
    if has_button:
        return GPIO.input(button_GPIO_pin)

#======================================================================================================
#Transmission controller (Fire & Forget)
def transmissionControl(sensitivity = 10, attempts = 5, print_delay = 30):
    printALERT("Beginning Transmission Controller")
    
    isReceiving = False
    isSending = False
    hasRelay = False
    
    #While not interupt sequence (i.e. forever)
    timeout = 300
    
    begin = time.monotonic()  # start timer
    last_print_idle = begin
    
    nrf.open_rx_pipe(0, address)
    nrf.listen = True
    
    while time.monotonic() < begin + timeout:
        now = time.monotonic()
    
        #Check accelerometer for crash-level movement
        if getAccelVectorMag() > sensitivity or hasRelay or interupt():
            #Print that system is preparing to send and clear TIXO buffer
            printALERT("Incident Detected")
            
            #Set state machine to sending
            isSending = True
            
            #Begin transmitter
            nrf.open_tx_pipe(address)
            nrf.listen = False
            
            #attempt number
            attemptCycles = 0
            
            while isSending and attemptCycles <= attempts:
                res = sendData(packageData(severity = sensitivity))
                if res == True:
                    printOK("Transmisson Received in Full")
                    isSending = False
                else:
                    printERR("Trying Again...")
                    attemptCycles += 1
                print("=" * 40)
            
            #In any case, no relay is present so reset flag
            hasRelay = False
            
            nrf.listen = True
            nrf.open_rx_pipe(0, address)
            
        #Has ANY data been received?
        elif nrf.any():
            
            #Print that system is preparing to receive and clear FIXO buffer
            printALERT("Transmission Detected")
            
            #Set state machine to receiving
            isReceiving = True
            
            #attempt number
            attemptCycles = 0
            
            while isReceiving and attemptCycles < attempts:
                attemptCycles += 1
                isReceiving = not receiveData()
                    
                #if list OK, send ACK and stop receiving by isReceiving = False
                #else if fails, send fail ACK and listen for new string
                printDIAG("Is Receiving Data: " + str(isReceiving))
                print("=" * 40)
                
        elif now - last_print_idle > print_delay:
            last_print_idle = now
            getGPSLock()
            printOK("Idle @ " + str(datetime.utcnow())[0:22])

def receiveData():
    now = time.monotonic()
    buffer = []
    
    while time.monotonic() < now + 2:
        if nrf.any():
            rx = nrf.recv()
            buffer.append(rx)
            
            print("Received (raw): {}".format(rx.decode('utf_8')))
    result = unpackageData(buffer)
    return result[1]

def sendData(l):
    printDIAG("Sending Data")
    result = nrf.send(l)
    if False in result:
        return False
    else:
        return True
    

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

has_GPS = cfg.config['has_GPS']
has_radio = cfg.config['has_radio']
has_accel = cfg.config['has_accel']
has_button = cfg.config['has_button']

initializeHardware(display_diagnostics = False, has_radio = cfg.config['has_radio'], has_accel = has_accel, has_GPS = has_GPS, has_button = has_button, button_pin = button_GPIO_pin, ch = 120)
transmissionControl()