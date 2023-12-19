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
        logging.info("QApplication created.")

       # self.stebim_process = subprocess.Popen(['python', 'StebimV3.py'])
       # logging.info("Stebim process started.")

        self.main_window = MonitorUI()
        logging.info("MonitorUI instance created.")

        self.machine_monitor = MachineMonitor("192.168.1.228", self.main_window.updateUI)
        logging.info("MachineMonitor initialized.")

        self.main_window.setMonitor(self.machine_monitor)
        logging.info("MachineMonitor set in MonitorUI.")

        self.app.aboutToQuit.connect(self.before_exit)
        logging.info("Handlers for application termination set.")

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s:%(levelname)s:%(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("application.log")
            ]
        )

    def before_exit(self):
        logging.info("Exiting application.")
        self.main_window.closeEvent()
        #self.stebim_process.terminate()

    def run(self):
        try:
            logging.info("Attempting to show GUI.")
            self.main_window.show()

            sys.exit(self.app.exec_())

        except Exception as e:
            logging.exception("An error occurred while starting the application")


def main():
    application = Application()
    logging.info("Application instance created.")
    application.run()


if __name__ == "__main__":
    main()