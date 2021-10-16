from src import accelerometer
from smbus import SMBus
import time
import adafruit_hts221
import busio
import board

print("Création capteur humidité ...")
h = adafruit_hts221.HTS221(busio.I2C(board.SCL, board.SDA))
print("Création acceleromètre ...")
a = accelerometer.Accelerometer(i2c_bus=SMBus(1))

a.active()
print("Capture de données pendant 5 secondes :")
start = time.monotonic()
last_t = time.monotonic()
try:
    while time.monotonic() - start < 5:

        # On enregistre les mesures 10 fois par seconde, sinon on passe le tour
        t = time.monotonic()
        if t - last_t < 0.1:
            continue
        last_t = t

        # Acceleromètre
        ax, ay, az = a.get_accel()
        print("accel :", ax, ay, az)
        print("hum", h.relative_humidity)

except (InterruptedError, KeyboardInterrupt):
    pass

print("Capture terminée, passage en mode veille ...")
a.standby()
print("Terminé !")

