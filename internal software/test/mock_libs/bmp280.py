import random

__version__ = '0.0.3'

CHIP_ID = 0x58
I2C_ADDRESS_GND = 0x76
I2C_ADDRESS_VCC = 0x77






class BMP280:
    def __init__(self, i2c_addr=I2C_ADDRESS_GND, i2c_dev=None):
        return

    def setup(self, mode='normal', temperature_oversampling=16, pressure_oversampling=16, temperature_standby=500):
        return

    def update_sensor(self):
        return

    def get_temperature(self):
        return random.randint(-5, 25) + random.random()

    def get_pressure(self):
        return random.randint(900, 1050) + random.random()

    def get_altitude(self, qnh=1013.25, manual_temperature=None):
        return random.randint(1, 500) + random.random()

    def set_mode(self, mode):
        return
