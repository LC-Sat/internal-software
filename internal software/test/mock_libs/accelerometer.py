import random

class Accelerometer:

    def __init__(self, i2c_addr=0x1C, i2c_bus=None):
        pass

    def get_accel(self):
        return random.randint(-2048, 2047), random.randint(-2048, 2047), random.randint(-2048, 2047)

    def active(self):
        return

    def standby(self):
        return
