"""
Example of library usage for streaming multiple payloads.
"""
import time
import board
import hashlib
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

def checkSHA1Checksum(l):
    h = hashlib.new('sha1')
    v= ''
    
    #Add each value in l in string form without START, END, and CHECKSUM
    for s in l[1:-3]:
        v = v +str(s)
        
    #Decode data
    h.update(bytes(v.encode('ASCII')))
    incoming_hash = l[l.index('Checksum')+1]
                      
    hash_len = len(incoming_hash)
    generated_hash = h.hexdigest()[0:hash_len]
    print("\nGenerated hash: " + generated_hash)
    if (generated_hash == incoming_hash):
        return True
    

def slave(timeout=5):
    """Stops listening after timeout with no response"""
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    # pipe number options range [0,5]
    # the pipe numbers used during a transition don't have to match
    nrf.open_rx_pipe(0, address)
    nrf.listen = True  # put radio into RX mode and power up

    rec = []
    now = time.monotonic()  # start timer
    while time.monotonic() < now + timeout:
        if nrf.any():
            # retreive the received packet's payload
            rx = nrf.recv()  # clears flags & empties RX FIFO
            msg = rx.decode('ASCII')
            rec.append(msg)
            print("Received (raw): {}".format(rx.decode('ASCII')))
            
            if msg == 'END' and 'BEGIN' in rec:
                break
                
            now = time.monotonic()
            
    #trim to correct data :]
    useful_data = rec[rec.index('BEGIN'):]
    if checkSHA1Checksum(useful_data) == True:
        print('Data Integrity OK \nPROCEED')
        #read in data for processing
    else:
        print('Data Integrity FAILED\nRETRY')
        #ask transmitter to retry
        
    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False  # put the nRF24L01 is in TX mode

print("""\
    nRF24L01 Stream test\n\
    Run slave() on receiver\n\
    Run master() on transmitter\n""")
slave(30)