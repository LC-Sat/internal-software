# import RPi.GPIO as GPIO  # import the GPIO library
import time  # import the time library
import winsound

class Buzzer(object):
    # Tunes :
    TUNE_STARTUP = 0
    TUNE_READY = 1
    TUNE_CAPTURE_START = 2
    TUNE_CAPTURE_STOP = 3
    TUNE_WIFI_ON = 4
    TUNE_WIFI_OFF = 5
    TUNE_SHUTDOWN = 6
    TUNE_SHUTDOWN_READY = 7
    TUNE_ERROR = 8

    tunes = [([261.63, 329.63, 392],  # Startup
              [0.1, 0.1, 0.1]),
             ([392, 523.25],  # Ready
              [0.2, 0.2]),
             ([392, 0, 392, 0, 392],  # Capture start
              [0.15, 0.05, 0.15, 0.05, 0.15]),
             ([523.25, 392, 329.63, 261.63],  # Capture stop
              [0.1, 0.1, 0.1, 0.1]),
             ([261.63, 392],  # Wifi on
              [0.2, 0.2]),
             ([392, 261.63],  # Wifi off
              [0.2, 0.2]),
             ([523.25, 392, 329.63],  # Shutdown en cours
              [0.1, 0.1, 0.1]),
             ([329.63, 261.63],  # Shutdown fini
              [0.2, 0.2]),
             ([329.63],
              [0.7])
             ]

    def __init__(self, pin):
        self.buzzer_pin = pin  # set to GPIO pin 5

    def __del__(self):
        class_name = self.__class__.__name__

    def _buzz(self, pitch, duration):

        if pitch == 0:
            time.sleep(duration)
            return
        pwm = GPIO.PWM(self.buzzer_pin, pitch)
        pwm.start(50)
        time.sleep(duration)
        pwm.stop()

    def buzz(self, pitch, duration):
        if pitch == 0:
            time.sleep(duration)
            return
        winsound.Beep(round(pitch), round(duration*1000))

    def play(self, tune):
        x = 0

        pitches, duration = self.tunes[tune]
        for p in pitches:
            self.buzz(p, duration[x])  # feed the pitch and duration to the function, “buzz”
            time.sleep(0.05)
            x += 1


if __name__ == "__main__":
    b = Buzzer(17)