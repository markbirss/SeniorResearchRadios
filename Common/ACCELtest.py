import board
import busio
import adafruit_lsm303_accel
import adafruit_lsm303dlh_mag
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import math


#Initialize accelerometer over I2C bus
i2c = busio.I2C(board.SCL, board.SDA)
mag = adafruit_lsm303dlh_mag.LSM303DLH_Mag(i2c)
accel = adafruit_lsm303_accel.LSM303_Accel(i2c)

#A lot of this caode can probably be looped/consolidated, the animate function seems slow
scanLength = 51

xAx = [i for i in range(scanLength)]
xAy = [0 for i in range(scanLength)]

yAx = [i for i in range(scanLength)]
yAy = [0 for i in range(scanLength)]

zAx = [i for i in range(scanLength)]
zAy = [0 for i in range(scanLength)]

fig = plt.figure()
ax1 = fig.add_subplot(3, 1, 1)
ax2 = fig.add_subplot(3, 1, 2)
ax3 = fig.add_subplot(3, 1, 3)

plt.subplots_adjust(hspace=1)

def animate(i, xAx, xAy, yAx, yAy, zAx, zAy):

    xAccel = accel.acceleration[0]
    yAccel = accel.acceleration[1]
    zAccel = accel.acceleration[2]
    
    mag = math.sqrt(xAccel**2)
    print(mag)

    # Add x and y to lists
    xAy.append(xAccel)
    yAy.append(yAccel)
    zAy.append(zAccel)

    xAx = xAx[-scanLength:]
    xAy = xAy[-scanLength:]
    
    yAx = yAx[-scanLength:]
    yAy = yAy[-scanLength:]
    
    zAx = zAx[-scanLength:]
    zAy = zAy[-scanLength:]

    # Draw x and y lists
    ax1.clear()
    ax1.plot(xAx, xAy)
    
    ax2.clear()
    ax2.plot(yAx, yAy)
    
    ax3.clear()
    ax3.plot(zAx, zAy)

    # Format plot
    ax1.set_title('X acceleration')
    ax1.set_xlabel('Samples')
    ax1.set_ylabel('m/s^2')
    ax2.set_title('Y acceleration')
    ax2.set_xlabel('Samples')
    ax2.set_ylabel('m/s^2')
    ax3.set_title('Z acceleration')
    ax3.set_xlabel('Samples')
    ax3.set_ylabel('m/s^2')
     
ani = animation.FuncAnimation(fig, animate, fargs=(xAx, xAy, yAx, yAy, zAx, zAy), interval=250, cache_frame_data=False)
plt.show()