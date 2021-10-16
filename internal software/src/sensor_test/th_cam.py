from src import amg88xx
import busio
import time
import board

cam = amg88xx.AMG88XX(busio.I2C(board.SCL, board.SDA))

print("Sortie du mode veille ...")
cam.set_mode(amg88xx._NORMAL_MODE)
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

        print(cam.pixels)

except (InterruptedError, KeyboardInterrupt):
    pass

print("Capture terminée, passage en mode veille ...")
cam.set_mode(amg88xx._SLEEP_MODE)
print("Terminé !")

