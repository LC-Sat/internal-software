import time
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus


class Accelerometer:

    def __init__(self, i2c_addr=0x1D, i2c_bus=None):
        self.addr = i2c_addr
        self.bus = i2c_bus

        self.standby()

        # Select Configuration Register(0x0E), set range to +/- 2g (0x00)
        self.bus.write_byte_data(self.addr, 0x0E, 0x01)

    def get_accel(self):
        # Read data back from 0x00, 7 bytes
        # Status register, X-Axis MSB, X-Axis, LSB, Y-Axis MSB, Y-Axis, LSB, Z-Axis MSB, Z-Axis, LSB,
        data = self.bus.read_i2c_block_data(self.addr, 0x00, 7)

        # Convert the data
        ax = (data[1] * 256 + data[2]) / 16
        if ax > 2047:
            ax -= 4096

        ay = (data[3] * 256 + data[4]) / 16
        if ay > 2047:
            ay -= 4096

        az = (data[5] * 256 + data[6]) / 16
        if az > 2047:
            az -= 4096

        return ax, ay, az

    def active(self):
        # Select Control Register(0x2A), Active mode (0x01)
        self.bus.write_byte_data(self.addr, 0x2A, 0x01)

    def standby(self):
        # Select Control Register(0x2A), StandBy mode (0x00)
        self.bus.write_byte_data(self.addr, 0x2A, 0x00)
