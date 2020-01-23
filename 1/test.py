"""
Example of library usage for streaming multiple payloads.
"""
import time
import board
import digitalio as dio
from circuitpython_nrf24l01 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
address = b'1Node'

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D8)
csn = dio.DigitalInOut(board.D17)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce, ard=250, arc=15, data_rate=1)

def generateSHA1Checksum(l):
    h = hashlib.new('sha1')
    v= ''
    
    #Add each value in l in string form
    for s in l:
        v = v +str(s)
       
    #Put into bytearray for hashing
    h.update(bytes(v.encode('ASCII')))
    l.append('Checksum')
    l.append(h.hexdigest())
    return l

def addBeginAndEndSeq(l):
    l.insert(0, 'BEGIN')
    l.append('END')
    return l

# lets create a list of payloads to be streamed to the nRF24L01 running slave()
toEncode = ['Lat', 39.095093, 'Long', -77.518437, 'Speed', 0.15, 'ID #', 10101010, 'Severity', 5, 'Relay', 1]

#Modified SHA-512 checksum pre-transmission
toEncode = generateSHA512Checksum(toEncode)
toEncode = addBeginAndEndSeq(toEncode)

buffer = []
for s in toEncode:
    buff = bytes(str(s).encode('ASCII'))
    buffer.append(buff)
    
#Generate and append checksum


def master(count=1):  # count = 5 will transmit the list 5 times
    """Transmits a massive buffer of payloads"""
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)
    # ensures the nRF24L01 is in TX mode
    nrf.listen = False

    success_percentage = 0
    for _ in range(count):
        now = time.monotonic() * 1000  # start timer
        
        #returns True for each element successfully sent. Possibly send in pairs dictionary style to confirm receipt
        #if result contains false send again up to 3 times? 
        result = nrf.send(buffer)
        
        print('Transmission took', time.monotonic() * 1000 - now, 'ms') 
        for r in result:
            #break out of method if failure
            if r==False:
                return False
            
            success_percentage += 1 if r else 0
    success_percentage /= (len(buffer)) * count
    print('Successfully sent', success_percentage * 100, '%')
    return True

print("""\
    nRF24L01 Stream test\n\
    Run slave() on receiver\n\
    Run master() on transmitter""")

#Can be packaged to access master and initiate comms
x = 1
while x <= 3:
    print('=' * 40)
    print('Attempt ',x)
    v = master(1)
    if(v == False):
        x+=1
        print('Failed, retrying...')
    else:
        print('Success, exiting...')
        break
