import time
import pickle
import numpy as np
import pyAesCrypt
import io
import os
import tarfile
import threading
import argparse

import RPi.GPIO as GPIO

# Application web pour le contrôle à distance
import webapp as app

# Capteurs
from picamera import PiCamera
from bmp280 import BMP280
from accelerometer import Accelerometer
# import amg88xx # TODO: CAM THERMIQUE
import adafruit_hts221

import board
import busio
import adafruit_gps
# import adafruit_amg88xx
from buzzer import Buzzer
from smbus import SMBus

# Logging configuration
import logging

log = logging.getLogger("cansat")
log.setLevel(logging.DEBUG)
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler("log.txt")
c_handler.setLevel(logging.INFO)
f_handler.setLevel(logging.DEBUG)

log_format = logging.Formatter(fmt="[%(asctime)s] [%(name)s/%(lineno)d] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
c_handler.setFormatter(log_format)
f_handler.setFormatter(log_format)
log.addHandler(c_handler)
log.addHandler(f_handler)

# Dossier de base pour les données
DATA_FOLDER = "/media/pi/2911-B16A1/data"

# Pins
_PIN_BUZZ = 17
_PIN_WIFI_SWITCH = 27

# Bus pour les capteurs
_BUSIO_BUS = busio.I2C(board.SCL, board.SDA)
_SMBUS_BUS = SMBus(1)
_BUS_BMP = _SMBUS_BUS
_BUS_ACCEL = _SMBUS_BUS
_BUS_GPS = _BUSIO_BUS
_BUS_THERM = _BUSIO_BUS
_BUS_HUM = _BUSIO_BUS

MODE_AUTO = 0
MODE_MANUAL = 1
MODE_DELAY = 2


class Cansat:

    # TODO:  détection de chute  / activation auto
    CAM_OUT = DATA_FOLDER + "/cam.mp4"
    CAM_OUT_CRYPT = DATA_FOLDER + "/cam.mp4.aes"
    OUT_FILE = DATA_FOLDER + "/data.bin.aes"
    DATA_ID_FILE = DATA_FOLDER + "/dataid"
    ZIP_OUT = DATA_FOLDER + "/data{}.tar.gz"

    def __init__(self, key=None, bufsize=4*1024, mode=MODE_DELAY, start_delay=60, stop_delay=60, debug=False, encryption=True):
        """
        Initialise le CanSat
        :param mode: Mode de déclenchement de la prise de donnée. Valeurs possibles :
        AUTO : Détection de la chute pour le démarrage, et détection de l'atterrissage pour l'arrêt
        MANUAL : Déclenchement et arrêt manuel par la connexion / l'interrupteur wifi
        DELAY : Déclenchement à retardement
        :param start_delay: Délai en secondes avant le déclenchement de la prise de données en mode DELAY
        :param stop_delay: Durée en secondes de la prise de données en mode DELAY
        :param key: La clé de chiffrement
        :param bufsize: Taille du buffer utilisé pour chiffrer
        """

        log.info("Initializing cansat ...")

        _ = time.monotonic()

        self.__init_pins()

        self.buzzer = Buzzer(_PIN_BUZZ)

        self.encryption = encryption
        self.debug = debug
        self.shutdown_flag = False
        self.mode = mode
        self.buzzer_on = False  # Si le buzzer doit bipper
        self.wifi = True
        retries = 0
        max_retries = 10
        while not os.path.exists(DATA_FOLDER):
            if retries >= max_retries:
                log.fatal("Could not access data folder after " + str(max_retries) + "retries ! Switching to default data folder.")
                DATA_FOLDER = "data"
                if os.path.exists(DATA_FOLDER):
                    break
                else:
                    log.fatal("Could not access default data folder ! Stopping program.")
                self.buzzer.buzz(329.63, 1.5)
                exit(1)
            retries += 1
            log.error(
                "Error while accessing data folder (maybe sd card is not mounted ?) Waiting 5 seconds before retrying (" + str(
                    max_retries - retries) + " retries left) ...")
            time.sleep(5)
            continue

        try:
            with open(Cansat.DATA_ID_FILE, "r") as f:
                self.data_nb = int(f.readline().strip())
        except Exception:
            log.warning("Error while reading data id file ("+Cansat.DATA_ID_FILE+"). Creating a new one.")
            self.data_nb = 0
            with open(Cansat.DATA_ID_FILE, "w+") as f:
                f.write("0")
                f.flush()


        self.saving = False  # Permet de bloquer la prise de donnée si on est en train d'en sauvegarder

        # On démarre le serveur web
        self.app = app.app
        app.sat = self
        app.DATA_PATH = DATA_FOLDER
        threading.Thread(target=self.app.run, args=("0.0.0.0", 80, False)).start()

        if mode == MODE_DELAY:
            self.start_delay = start_delay
            self.stop_delay = stop_delay

        # play startup sound
        self.buzzer.play(Buzzer.TUNE_STARTUP)

        self._buf_size = bufsize

        if key is None:
            key = input("Please enter an encryption key : ")

        self.__key = key

        self.__init_values()

        # Initialisation des capteurs

        # Camera
        self.cam_enabled = True
        try:
            self.cam = PiCamera()
            self.cam.framerate = 30
        except Exception as e:
            log.error("Error while initializing camera. The camera will be disabled for this run.")
            log.error("Error : "+str(e))
            self.buzzer.play(Buzzer.TUNE_ERROR)
            if debug:
                raise e
            self.cam_enabled = False

        # BMP
        self.bmp_enabled = True
        try:
            self.bmp = BMP280(i2c_dev=_BUS_BMP)
            self.__init_bmp()
        except Exception as e:
            log.error("Error while initializing BMP Sensor. It will be disabled for this run.")
            log.error("Error : "+str(e))
            self.buzzer.play(Buzzer.TUNE_ERROR)
            if debug:
                raise e
            self.bmp_enabled = False

        # Acceleromètre
        self.accel_enabled = True
        try:
            self.accel = Accelerometer(i2c_bus=_BUS_ACCEL)
        except Exception as e:
            log.error("Error while initializing Accelerometer. It will be disabled for this run.")
            log.error("Error : "+str(e))
            self.buzzer.play(Buzzer.TUNE_ERROR)
            if debug:
                raise e
            self.accel_enabled = False

        # GPS
        self.gps_enabled = True
        try:
            self.gps = adafruit_gps.GPS_GtopI2C(_BUS_GPS)
            # Turn on the basic GGA and RMC info
            self.gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
            # Set update rate to 10 Hz (100 ms delay)
            self.gps.send_command(b"PMTK220,100")
            # self.gps.send_command(b"PMTK161,0")  # standby mode
        except Exception as e:
            log.error("Error while initializing GPS. It will be disabled for this run.")
            log.error("Error : "+str(e))
            self.buzzer.play(Buzzer.TUNE_ERROR)
            if debug:
                raise e
            self.gps_enabled = False

        # Caméra thermique
        self.th_cam_enabled = True
        try:
            # self.th_cam = amg88xx.AMG88XX(_BUS_THERM)
            # self.th_cam.set_mode(amg88xx._SLEEP_MODE)
            # TODO: CAM THERMIQUE
            self.th_cam_enabled = False
        except Exception as e:
            log.error("Error while initializing Thermal camera. It will be disabled for this run.")
            log.error("Error : " + str(e))
            self.buzzer.play(Buzzer.TUNE_ERROR)
            if debug:
                raise e
            self.th_cam_enabled = False

        # Humidité
        self.hum_enabled = True
        try:
            self.hum = adafruit_hts221.HTS221(_BUS_HUM)
        except Exception as e:
            log.error("Error while initializing Humidity sensor. It will be disabled for this run.")
            log.error("Error : " + str(e))
            self.buzzer.play(Buzzer.TUNE_ERROR)
            if debug:
                raise e
            self.hum_enabled = False

        self.capture = False
        self.capture_thread = None
        log.info("Initialization done. Starting ...")
        self.running = True
        self.main()

    def __init_pins(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(_PIN_WIFI_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(_PIN_BUZZ, GPIO.OUT)

    def __init_values(self):
        self.val = {}

        # BMP
        self.val["press"] = []
        self.val["temp"] = []
        self.val["alt"] = []

        # hts221
        self.val["hum"] = []

        # Accéléromètre
        self.val["ax"] = []
        self.val["ay"] = []
        self.val["az"] = []

        # GPS
        self.val["lat"] = []
        self.val["lon"] = []
        self.val["sat"] = []    # Nombre de satellites
        self.val["qual"] = []   # qualité du fix
        self.val["speed"] = []  # vitesse

        # Caméra thermique
        self.val["therm"] = []

    def __init_bmp(self, nb_values=20, delay=0.5):
        """
        Initialise le capteur Altitude Pression Température (BMP280) en récupérant le QNH pour mesurer l'altitude.
        :param nb_values: Nombre de mesures à prendre
        :param delay: Délai entre chaque mesure
        """

        values = []
        for _ in range(nb_values):
            values.append(self.bmp.get_pressure())
            time.sleep(delay)

        self.qnh = sum(values) / len(values)  # On prends la moyenne des mesures

        # On désactive le capteur
        self.bmp.set_mode("sleep")

    def _enable_sensors(self):
        """Passe tout les capteurs en mode de prise de donnée."""
        if self.th_cam_enabled:
            # self.th_cam.set_mode(amg88xx._NORMAL_MODE) # TODO: CAM THERMIQUE
            pass

        if self.bmp_enabled:
            self.bmp.set_mode("normal")
        if self.accel_enabled:
            self.accel.active()

    def _disable_sensors(self):
        """Passe tout les capteurs en mode veille pour économiser de l'énergie."""
        if self.th_cam_enabled:
            # self.th_cam.set_mode(amg88xx._SLEEP_MODE) # TODO: CAM THERMIQUE
            pass
        if self.bmp_enabled:
            self.bmp.set_mode("sleep")
        # if self.gps_enabled:
        #     self.gps.send_command(b"PMTK161,0")  # standby mode
        if self.accel_enabled:
            self.accel.standby()

    def start_capture(self):
        if self.capture or self.saving:
            log.warning("Didn't start capture because already capturing or saving")
            log.debug("capture : " + str(self.capture) + "saving : " + str(self.saving))
            return
        self.capture = True
        log.info("Starting capture")
        self.buzzer.play(Buzzer.TUNE_CAPTURE_START)
        self.capture_thread = CaptureThread(self)
        self.capture_thread.start()

    def stop_capture(self):
        if not self.capture:
            log.warning("Didn't stop capture because not capturing")
            log.debug("capture : " + str(self.capture))
            return
        log.info("Stopping capture")
        self.buzzer.play(Buzzer.TUNE_CAPTURE_STOP)
        self.capture = False

    def start_buzzer(self):
        if self.buzzer_on:
            return
        self.buzzer_on = True
        threading.Thread(target=self.__buzz_loop).start()

    def stop_buzzer(self):
        self.buzzer_on = False

    def __buzz_loop(self):
        while self.buzzer_on:
            self.buzzer.buzz(524, 0.5)
            time.sleep(2.5)

    def _save_data(self, data_file=OUT_FILE):
        """
        Enregistre les données dans un fichier crypté.
        Supprime toutes les données de la mémoire.
        :param data_file: Le fichier dans lequel sauvegarder les données
        """
        # On convertit toutes les données en array numpy

        self.saving = True
        log.info("Saving data ...")

        try:
            # GPS
            self.val["lat"] = np.array(self.val["lat"], dtype=np.float32)
            self.val["lon"] = np.array(self.val["lon"], dtype=np.float32)
            # self.val["sat"] = np.array(self.val["sat"], dtype=np.uint8)
            # self.val["qual"] = np.array(self.val["qual"], dtype=np.uint8)
            # self.val["speed"] = np.array(self.val["speed"], dtype=np.float16)

            self.val["sat"] = np.zeros(1, dtype=np.uint8)
            self.val["qual"] = np.zeros(1, dtype=np.uint8)
            self.val["speed"] =np.zeros(1, dtype=np.float16)

            # BMP
            self.val["press"] = np.array(self.val["press"], dtype=np.float32)
            self.val["temp"] = np.array(self.val["temp"], dtype=np.float16)
            self.val["alt"] = np.array(self.val["alt"], dtype=np.float16)

            # Humidité
            self.val["hum"] = np.array(self.val["hum"], dtype=np.float16)

            # Acceleromètre
            self.val["ax"] = np.array(self.val["ax"], dtype=np.int16)
            self.val["ay"] = np.array(self.val["ay"], dtype=np.int16)
            self.val["az"] = np.array(self.val["az"], dtype=np.int16)

            # Caméra thermique
            self.val["therm"] = np.array(self.val["therm"], dtype=np.float16)

            if self.encryption:
                # Encrypt the data in a file
                val = pickle.dumps(self.val)
                val = io.BytesIO(val)

                log.info("Encrypting data ...")
                log.debug("Data ...")
                with open(data_file, "wb") as outf:
                    pyAesCrypt.encryptStream(val, outf, self.__key, self._buf_size)

                log.debug("Done")

                # Cryptage de la vidéo
                if self.cam_enabled:
                    log.debug("Video")
                    pyAesCrypt.encryptFile(self.CAM_OUT, self.CAM_OUT_CRYPT, self.__key, self._buf_size)

                    log.debug("Done")

                    # On supprime la vidéo non cryptée
                    if os.path.exists(self.CAM_OUT):
                        os.remove(self.CAM_OUT)

                cam_file = self.CAM_OUT_CRYPT

            else:
                log.debug("Saving data ...")
                try:
                    with open(data_file, "wb") as outf:
                        pickle.dump(self.val, outf)
                except IOError:
                    log.error("Error while saving data ! Skipping ...")
                log.debug("Done")
                cam_file = self.CAM_OUT

            # On réinitialise les valeurs
            self.__init_values()

            log.info("Compressing ...")
            # On compresse les données
            tar = tarfile.open(self.ZIP_OUT.format(self.data_nb), mode="w:gz")
            if self.cam_enabled:
                tar.add(cam_file)
            tar.add(self.OUT_FILE)
            tar.close()

            # On supprime les données non compressées
            if os.path.exists(self.CAM_OUT_CRYPT):
                os.remove(self.CAM_OUT_CRYPT)

            if os.path.exists(data_file):
                os.remove(data_file)

            log.info("Done !")

            self.data_nb += 1
            with open(Cansat.DATA_ID_FILE, "w") as f:
                f.write(str(self.data_nb))
                f.flush()

        except Exception as e:
            log.error("Error while saving data !")
            log.error("Error : "+str(e))
            self.buzzer.play(Buzzer.TUNE_ERROR)

        self.saving = False

    def main(self):
        """Boucle principale du cansat"""
        self.running = True
        self.buzzer.play(Buzzer.TUNE_READY)  # Son cansat prêt)
        log.info("Running")
        wifi = GPIO.input(_PIN_WIFI_SWITCH)
        log.debug("wifi : " + str(self.wifi) + "switch : " + str(wifi))

        if self.mode == MODE_DELAY:
            start = time.monotonic()

        wifi_time = None
        while self.running:

            # On récupère l'état de l'interrupteur wifi
            wifi = GPIO.input(_PIN_WIFI_SWITCH)

            if wifi_time is not None and wifi == self.wifi:
                log.debug("Wifi switch quick switch detected")
                log.debug("wifi_time : " + str(wifi_time) + " current time : " + str(time.monotonic()) + " wifi : " + str(wifi) + " cansat_wifi : " + str(self.wifi))
                # On a un temps enregistré et on est dans le même état, on a fait un aller retour -> switch capture
                wifi_time = None
                if self.capture:
                    log.debug("Stopping capture (from main)")
                    self.stop_capture()
                else:
                    log.debug("Starting capture (from main)")
                    self.start_capture()

            # Gestion du wifi / prise de donnée en mode manuel
            if wifi != self.wifi:  # Interrupteur pas dans le même état que le wifi

                if wifi:

                    # On passe de désactivé à activé
                    if wifi_time is None:
                        log.debug("Switch detected (off -> on) at " + str(time.monotonic()))
                        # On enregistre la date ou l'interrupteur à été activé
                        wifi_time = time.monotonic()

                    elif time.monotonic() - wifi_time > 2:
                        log.debug("waited 2 sec, enabling wifi")
                        log.debug("wifi_time : " + str(wifi_time) + " current time : " + str(time.monotonic()) + " wifi : " + str(wifi) + " cansat_wifi : " + str(self.wifi))
                        # on a attendu plus de 2 secondes, on active le wifi
                        wifi_time = None
                        self._enable_wifi()

                else:
                    # On passe d'activé à désactivé
                    if wifi_time is None:
                        log.debug("Switch detected (on -> off) at " + str(time.monotonic()))
                        # On enregistre la date ou l'interrupteur à été désactivé
                        wifi_time = time.monotonic()

                    elif time.monotonic() - wifi_time > 2:
                        log.debug("waited 2 sec, disabling wifi")
                        log.debug("wifi_time : " + str(wifi_time) + " current time : " + str(time.monotonic()) + " wifi : " + str(wifi) + " cansat_wifi : " + str(self.wifi))
                        # on a attendu plus de 2 secondes, on désactive le wifi
                        wifi_time = None
                        self._disable_wifi()

            if self.mode == MODE_DELAY:

                if not self.capture and time.monotonic() - start > self.start_delay:
                    log.debug("Capture started from delay mode")
                    start = time.monotonic()
                    self.start_capture()
                else:
                    if time.monotonic() - start > self.stop_delay:
                        log.debug("Capture stopped from delay mode")
                        self.stop_capture()
                        self.running = False
                        break

            if self.mode == MODE_AUTO:

                # TODO: Détecter la chute / l'atterrissage pour activer / désactiver les données

                pass

        if self.shutdown_flag:  # On est en train d'éteindre le cansat, pas besoin de faire bipper
            return

        # On active le buzzer de récupération
        self.start_buzzer()

        # On attend que le bouton du wifi soit allumé puis éteint / éteint puis allumé pour éteindre le buzzer
        w_switch = self.wifi
        while w_switch == GPIO.input(_PIN_WIFI_SWITCH):
            pass
        w_switch = GPIO.input(_PIN_WIFI_SWITCH)
        while w_switch == GPIO.input(_PIN_WIFI_SWITCH):
            pass

        # On désactive le buzzer
        self.stop_buzzer()

        # Dernière boucle pour le wifi et l'arrêt
        wifi_time = None
        while self.running:

            # On récupère l'état de l'interrupteur wifi
            wifi = GPIO.input(_PIN_WIFI_SWITCH)

            # Gestion du wifi / prise de donnée en mode manuel
            if wifi != self.wifi:  # Interrupteur pas dans le même état que le wifi

                if wifi:
                    self._enable_wifi()

                else:
                    self._disable_wifi()

    def shutdown(self):
        """Eteint le cansat correctement"""
        self.shutdown_flag = True
        self.running = False
        log.info("Shutting down ...")

        self.buzzer.play(Buzzer.TUNE_SHUTDOWN)

        if self.capture:
            log.debug("Stopping capture (shutdown)")
            self.stop_capture()
            time.sleep(1)
            
        # On attends que la sauvegarde soit finie
        while self.saving:
            continue
            
        # On joue le son de shutdown
        self.buzzer.play(Buzzer.TUNE_SHUTDOWN_READY)
        exit()

    def _enable_wifi(self):
        if self.wifi:
            return
        self.wifi = True
        log.info("Enabling wifi ...")
        self.buzzer.buzz(392, 0.2)
        threading.Thread(target=self.__enable_wifi())

    def __enable_wifi(self):
        os.system("sudo ./enableAP.sh")
        log.info("Wifi successfully enabled !")
        self.buzzer.play(Buzzer.TUNE_WIFI_ON)

    def _disable_wifi(self):
        if not self.wifi:
            return
        self.wifi = False
        log.info("Disabling wifi ...")
        self.buzzer.buzz(392, 0.2)
        threading.Thread(target=self.__disable_wifi())

    def __disable_wifi(self):
        os.system("sudo ./disableAP.sh")
        log.info("Wifi successfully disabled !")
        self.buzzer.play(Buzzer.TUNE_WIFI_OFF)


class CaptureThread(threading.Thread):

    def __init__(self, cansat):
        self.sat = cansat
        threading.Thread.__init__(self)

    def run(self):

        self.sat._enable_sensors()

        if self.sat.cam_enabled:
            self.sat.cam.start_recording(self.sat.CAM_OUT)

        last_t = time.monotonic() + 10
        try:
            while self.sat.capture:

                # gps.update() doit être appelé au moins 2 fois plus régulièrement que la prise de données, donc
                # on l'appelle à chaque tour de boucle
                if self.sat.gps_enabled:
                    self.sat.gps.update()

                # On enregistre les mesures 10 fois par seconde, sinon on passe le tour
                t = time.monotonic()
                if t - last_t < 0.1:
                    continue
                last_t = t

                # BMP280
                if self.sat.bmp_enabled:
                    self.sat.val["press"].append(self.sat.bmp.get_pressure())
                    self.sat.val["temp"].append(self.sat.bmp.get_temperature())
                    self.sat.val["alt"].append(self.sat.bmp.get_altitude(qnh=self.sat.qnh))
                else:
                    self.sat.val["press"].append(None)
                    self.sat.val["temp"].append(None)
                    self.sat.val["alt"].append(None)

                # Humidité
                if self.sat.hum_enabled:
                    self.sat.val["hum"].append(self.sat.hum.relative_humidity)
                else:
                    self.sat.val["hum"].append(None)

                # Acceleromètre
                if self.sat.accel_enabled:
                    ax, ay, az = self.sat.accel.get_accel()
                else:
                    ax, ay, az = None, None, None
                self.sat.val["ax"].append(ax)
                self.sat.val["ay"].append(ay)
                self.sat.val["az"].append(az)

                # Caméra thermique
                if self.sat.th_cam_enabled:
                    self.sat.val["therm"].append(self.sat.th_cam.pixels)  # TODO: CAM THERMIQUE
                else:
                    self.sat.val["therm"].append(np.zeros((8, 8)))

                # GPS
                if self.sat.gps_enabled and self.sat.gps.has_fix:
                    self.sat.val["lat"].append(self.sat.gps.latitude)
                    self.sat.val["lon"].append(self.sat.gps.longitude)
                    self.sat.val["sat"].append(self.sat.gps.satellites)
                    self.sat.val["qual"].append(self.sat.gps.fix_quality)
                    self.sat.val["speed"].append(self.sat.gps.speed_knots)
                else:
                    # Si on a pas de fix, on met des valeurs vides
                    self.sat.val["lat"].append(None)
                    self.sat.val["lon"].append(None)
                    self.sat.val["sat"].append(None)
                    self.sat.val["qual"].append(None)
                    self.sat.val["speed"].append(None)

        except (InterruptedError, KeyboardInterrupt):
            pass

        if self.sat.cam_enabled:
            self.sat.cam.stop_recording()

        self.sat._disable_sensors()
        self.sat._save_data()

        # self.sat.__key = None  # On supprime la clé pour qu'elle ne puisse pas être récupérée
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Démarre le système principal du cansat.")
    parser.add_argument("-k", "--key", help="Clé de cryptage", default="cansat2021")
    parser.add_argument("-d", "--debug", help="Active le mode de débug", action="store_true")
    namespace = parser.parse_args()
    sat = Cansat(key=namespace.key, mode=MODE_MANUAL)
