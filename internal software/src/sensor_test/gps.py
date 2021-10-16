import adafruit_gps
import board
import busio
import time

# GPS
gps = adafruit_gps.GPS_GtopI2C(busio.I2C(board.SCL, board.SDA))
# Turn on the basic GGA and RMC info
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
# Set update rate to 10 Hz (100 ms delay)
gps.send_command(b"PMTK220,100")
# gps.send_command(b"PMTK161,0")  # standby mode

# Wait for fix
waitfix = True

if waitfix:
    print("Waiting for fix ...")
    while not gps.has_fix:
        gps.update()

print("Capture de données pendant 5 secondes :")
start = time.monotonic()
last_t = time.monotonic()
try:
    while time.monotonic() - start < 5:

        # gps.update() doit être appelé au moins 2 fois plus régulièrement que la prise de données, donc
        # on l'appelle à chaque tour de boucle
        gps.update()

        # On enregistre les mesures 10 fois par seconde, sinon on passe le tour
        t = time.monotonic()
        if t - last_t < 0.1:
            continue
        last_t = t

        # GPS
        if gps.has_fix:
            print(gps.latitude)
            print(gps.longitude)
            print(gps.satellites)
            print(gps.fix_quality)
            print(gps.speed_knots)
        else:
            print("NO FIX")

except (InterruptedError, KeyboardInterrupt):
    pass

print("Capture terminée, passage en mode veille ...")
# gps.send_command(b"PMTK161,0")
print("Terminé !")

