import webapp as app
import time
import threading

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


class MockCansat:

    def __init__(self):

        log.info("Initializing cansat ...")
        self.encryption = True
        self.debug = False
        self.shutdown_flag = False
        self.mode = 1
        self.buzzer_on = False  # Si le buzzer doit bipper
        self.wifi = False
        self.saving = False  # Permet de bloquer la prise de donnée si on est en train d'en sauvegarder
        self.data_nb = 2

        # On démarre le serveur web
        self.app = app.app
        app.sat = self
        app.DATA_PATH = "."
        threading.Thread(target=self.app.run, args=("0.0.0.0", 80, False)).start()

        self.cam_enabled = True
        self.bmp_enabled = True
        self.accel_enabled = True
        self.gps_enabled = True

        self.th_cam_enabled = False
        log.error("Error while initializing Thermal camera. It will be disabled for this run.")
        self.hum_enabled = True

        self.capture = False
        log.info("Initialization done. Starting ...")
        self.running = True
        self.main()


    def start_capture(self):
        if self.capture or self.saving:
            log.warning("Didn't start capture because already capturing or saving")
            log.debug("capture : " + str(self.capture) + "saving : " + str(self.saving))
            return
        self.capture = True
        log.info("Starting capture")

    def stop_capture(self):
        if not self.capture:
            log.warning("Didn't stop capture because not capturing")
            log.debug("capture : " + str(self.capture))
            return
        log.info("Stopping capture")
        self.capture = False

    def start_buzzer(self):
        if self.buzzer_on:
            return
        self.buzzer_on = True

    def stop_buzzer(self):
        self.buzzer_on = False

    def main(self):
        """Boucle principale du cansat"""
        self.running = True
        log.info("Running")

    def shutdown(self):
        """Eteint le cansat correctement"""
        self.shutdown_flag = True
        self.running = False
        log.info("Shutting down ...")

        if self.capture:
            log.debug("Stopping capture (shutdown)")
            self.stop_capture()
            time.sleep(1)

        # On attends que la sauvegarde soit finie
        while self.saving:
            continue
        exit()


if __name__ == "__main__":
    sat = MockCansat()
