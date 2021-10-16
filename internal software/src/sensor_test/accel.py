from .. import accelerometer
from smbus import SMBus
import time

a = accelerometer.Accelerometer(i2c_bus=SMBus(1), i2c_addr=0x1D)

print("Sortie du mode veille ...")
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
        print(ax, ay, az)

except (InterruptedError, KeyboardInterrupt):
    pass

print("Capture terminée, passage en mode veille ...")
a.standby()
print("Terminé !")

