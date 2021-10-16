import webapp.app
import threading


class Sat:

    def __init__(self):
        self.mode = 0
        self.capture = False
        self.running = True
        self.data_nb = 0


sat = Sat()

app = webapp.app.app
webapp.app.sat = sat

threading.Thread(target=app.run, args=("0.0.0.0", 80, False)).start()

