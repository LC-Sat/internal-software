from unittest.mock import Mock
import numpy as np


# Operating Modes
_NORMAL_MODE = 1
_SLEEP_MODE = 1
_STAND_BY_60 = 1
_STAND_BY_10 = 1

# frame rates
_FPS_10 = 1
_FPS_1 = 1


class AMG88XX:

    def __init__(self, i2c, addr=0x69):

        # set to 10 FPS
        self._fps = _FPS_10

    @property
    def temperature(self):
        return 25

    @property
    def pixels(self):
        return np.random.uniform(low=-5.0, high=25.0, size=(8, 8))

    def set_mode(self, mode):
        return

