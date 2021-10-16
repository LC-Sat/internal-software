from unittest.mock import Mock
import random


class GPS_GtopI2C:

    def __init__(self, a):
        self.has_fix = True
        super(GPS_GtopI2C, self).__init__()

    @property
    def latitude(self):
        return random.randint(-90, 90) + random.random()

    @property
    def longitude(self):
        return random.randint(-90, 90) + random.random()

    @property
    def fix_quality(self):
        return random.randint(-90, 90) + random.random()

    @property
    def satellites(self):
        return random.randint(1,15)

    @property
    def speed_knots(self):
        return random.randint(0, 15) + random.random()

    def __getattr__(self, item):
        return self.nothing

    def nothing(self, *args, **kwargs):
        return
