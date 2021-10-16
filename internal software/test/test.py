import unittest
import os
import sys
from unittest.mock import patch
import threading

mock_dir = os.path.join(os.path.dirname(__file__), "mock_libs")
assert(os.path.exists(mock_dir))
sys.path.insert(0, mock_dir)

from src import cansat


class FakeSat(threading.Thread):

    def __init__(self, mode=cansat.MODE_DELAY):
        self.mode = mode
        super(FakeSat, self).__init__()
        self.sat = cansat.Cansat(key="123456", mode=self.mode)
        self.start()

    def run(self):
        self.sat.main()

    def set_wifi(self, wifi):
        cansat.WIFI = wifi


def wifi_switch():
    try:
        while 1:
            print("Wifi switch :", cansat.WIFI)
            input()
            cansat.WIFI = not cansat.WIFI

    except (InterruptedError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    th = FakeSat(mode=cansat.MODE_MANUAL)

