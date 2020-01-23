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

def slave(timeout=5):
    """Stops listening after timeout with no response"""
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    # pipe number options range [0,5]
    # the pipe numbers used during a transition don't have to match
    nrf.open_rx_pipe(0, address)
    nrf.listen = True  # put radio into RX mode and power up

    count = 0
    now = time.monotonic()  # start timer
    while time.monotonic() < now + timeout:
        if nrf.any():
            count += 1
            # retreive the received packet's payload
            rx = nrf.recv()  # clears flags & empties RX FIFO
            
            #converts bytearray to normal python string
            print("Received (raw): {}".format(rx.decode('ASCII')))
            now = time.monotonic()

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False  # put the nRF24L01 is in TX mode

print("""\
    nRF24L01 Stream test\n\
    Run slave() on receiver\n\
    Run master() on transmitter""")
slave(30)