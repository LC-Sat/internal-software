from src import bmp280
from smbus import SMBus
import time

b = bmp280.BMP280(i2c_dev=SMBus(1))

print("Sortie du mode veille ...")
b.set_mode("normal")
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
        print(b.get_temperature(), b.get_pressure(), b.get_altitude())

except (InterruptedError, KeyboardInterrupt):
    pass

print("Capture terminée, passage en mode veille ...")
b.set_mode("sleep")
print("Terminé !")

