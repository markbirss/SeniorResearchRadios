# Senior Research Radios
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/Matthew1231A/SeniorResearchRadios?style=flat-square) ![GitHub last commit](https://img.shields.io/github/last-commit/Matthew1231A/SeniorResearchRadios?style=flat-square) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/adafruit-circuitpython-lsm303dlh-mag?style=flat-square)

This library meshed Raspberry Pi's with various sensors which combine to allow individual nodes to alert drivers of a crash.

## Required Repos and Libraries
The packaging of this repo right now is uncertain. These are the libraries used in making this project run. Thanks Adafruit!

```bash
sudo pip3 install circuitpython-nrf24l01
sudo pip3 install adafruit-circuitpython-gps
sudo pip3 install adafruit-circuitpython-lsm303-accel
sudo pip3 install adafruit-circuitpython-lsm303dlh-mag
```

## Usage

This repo requires the following hardware:
1. 2x Raspberry Pi 3B+
2. 2x NRF24L01+ Transceivers
3. Assorted Wires
    1. ~20x Female - Male Jumper Wires
    2. ~20x Male - Male Jumper Wires
    3. 1x [USB Breakout Wire](https://www.adafruit.com/product/954)
4. 1x Adafruit LSM303DLHC Accelerometer/Compass combo
5. 1x Adafruit GPS Breakout
6. 2x 10uF decoupling capacitors
7. 2x Breadboards (recommended 50x10)

Configure the Raspberry Pi's on a stock Raspbian build. All packages are confirmed to work with Raspbian 10 (Buster). 

Using `sudo raspi-config`, enable the SPI and I2C interfaces on both devices. Be sure to save. Use `sudo reboot` to have the changes stick. 

First, connect the NRF24L01+ transceivers. 

![Table](https://circuitdigest.com/sites/default/files/inlineimages/u/nRF24L01-RF-Module.png)

If your board has poor/nonexistent labeling, refer to [XYZpinout](https://pinout.xyz).

Next, the GPS to unit 1.

![Pinout](https://cdn-learn.adafruit.com/assets/assets/000/062/854/medium640/adafruit_products_sensors_usbgps_bb_narrow.png?1538431002)

Finally, the accelerometer ot unit 1 also. 

![Pinout](https://cdn-learn.adafruit.com/assets/assets/000/083/212/medium640/robotics___cnc_lsm303dlh_rpi_bb.jpg?1572379494)

Your hardware is ready. Now, the code!

Clone this repo using `git clone https://github.com/Matthew1231A/SeniorResearchRadios.git` and use `cd SeniorResearchRadios` to locate the repository. After installing the libraries above using the command line, run the files located within the folders 1 and 2. Folder 1 is the transmitter and folder 2 is the receiver. Eventually, both will be able to transcieve and no designation will be necessary.

When executed in Thonny, the included IDE, the master should return a confirmation and the slave should recieve the number sent. Updates to this readme will reflect code updates and changes.
