import sys
import logging
import subprocess
from PyQt5.QtWidgets import QApplication
from monitor_ui import MonitorUI
from machine_monitor import MachineMonitor


class Application:
    def __init__(self):
        self.setup_logging()
        logging.debug("Logging is set up. Starting GFlow application")
        self.app = QApplication(sys.argv)
        self.stebim_process = subprocess.Popen(['python', 'StebimV3.py'])
        self.main_window = MonitorUI()
        self.machine_monitor = MachineMonitor("192.168.1.228", self.main_window.updateUI)
        self.main_window.setMonitor(self.machine_monitor)
        self.app.aboutToQuit.connect(self.main_window.closeEvent)
        self.app.aboutToQuit.connect(lambda: self.stebim_process.terminate())

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s:%(levelname)s:%(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

    def run(self):
        try:
            self.main_window.show()
            sys.exit(self.app.exec_())
        except Exception as e:
            logging.exception("An error occurred while starting the application")


def main():
    application = Application()
    application.run()


if __name__ == "__main__":
    main()
