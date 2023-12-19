# Import necessary modules
import logging
import subprocess
import time
import os
import re
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from db_manager import DBManager


class MachineMonitor(QObject):


    status_updated = pyqtSignal(dict)

    def start_monitoring(self):
        if not self.thread:
            self.thread = QThread()
            self.moveToThread(self.thread)
            self.thread.started.connect(self.run)
            self.running = True
            self.thread.start()
        logging.info("Monitoring started.")

    def __init__(self, ip_address, update_callback=None):
        super().__init__()
        self.ip_address = ip_address
        self.update_callback = update_callback
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.running = True
        self.db_manager = DBManager()
        logging.info("MachineMonitor initialized.")

    def run(self):
        logging.info("Running MachineMonitor.")
        self.connect_to_machine()

        while self.running:
            try:
                logging.debug("Preparing to emit status_updated signal")
                # Inline Temp applied here and Emitting signals directly
                self.emit_status_update({
                    'status': self.getMachineStatus(),
                    'current_line': self.getCurrentProgramInfo()[2],
                    'selected_program': self.getCurrentProgramInfo()[0],
                    'current_program': self.getCurrentProgramInfo()[1],
                    'error_text': self.getMachineError()[0],
                    'error_class': self.getMachineError()[1]
                })
                logging.debug("Emitted status_updated signal successfully")
            except Exception as e:
                logging.debug("Error occurred, preparing to emit status_updated signal with error details")
                logging.exception("An error occurred in the run method.")
                # Inline Temp applied here and Emitting signals directly
                self.emit_status_update({
                    'status': 'Error',
                    'current_line': 0,
                    'selected_program': 'None',
                    'current_program': 'None',
                    'error_text': str(e),
                    'error_class': 'Exception'
                })
                logging.debug("Emitted status_updated signal successfully with error details")
            logging.debug("Sleeping for 10 seconds.")
            time.sleep(10)  # Adjust the sleep time as needed
        self.close_connection()

    def stop(self):
        self.running = False
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
            logging.info("MachineMonitor stopped.")

    def connect_to_machine(self):
        # Code to establish a connection to the machine
        self.process = subprocess.Popen(["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        logging.info("Connected to machine.")

    def reconnect_to_machine(self):
        # Attempt to re-establish the connection
        self.close_connection()
        self.connect_to_machine()
        logging.info("Reconnected to machine.")

    def close_connection(self):
        # Code to gracefully close the connection
        if self.process:
            self.process.terminate()
            self.process = None
        logging.info("Connection closed.")

    def _run_command(self, command_arguments):
        # Extract Method applied here, and it's used in methods like getMachineStatus, getCurrentProgramInfo, and getMachineError
        # The actual list of arguments would vary based on caller method and so it is passed as a parameter
        return subprocess.run(
            command_arguments,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def getMachineStatus(self):
        try:
            command_arguments = ["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address,
                                 "runinfo", "e"]
            result = self._run_command(command_arguments)
            logging.debug(f"Raw output for machine status: {result.stdout}")
            match = re.search(r'Execution Mode: (\d+) \((.*?)\)', result.stdout)
            if match:
                return match.group(2)
            else:
                logging.warning("Failed to parse machine status.")
                return "Unknown"
        except Exception as e:
            logging.error(f"Error in getMachineStatus: {e}")
            return "Error - " + str(e)





    def getTotalLinesOfCurrentProgram(self):
        try:
            current_program, _ = self.getCurrentProgramInfo()
            if current_program == "<No program active>":
                return 0, 0

            # Get the directory of the current script
            script_dir = os.path.dirname(__file__)
            program_path = os.path.join(script_dir, "NIGHT", current_program)

            if os.path.exists(program_path):
                with open(program_path, 'r') as file:
                    total_lines = sum(1 for _ in file)
            else:
                print(f"Program file not found: {program_path}")
                total_lines = 0

            current_line = self.getCurrentProgramInfo()
            return total_lines, current_line
        except Exception as e:
            print(f"Error in getTotalLinesOfCurrentProgram: {e}")
            return 0, 0

    def getCurrentProgramInfo(self):
        try:
            command_arguments = ["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address,
                                 "runinfo", "p"]
            result = self._run_command(command_arguments)
            logging.debug(f"Raw output for current program info: {result.stdout}")

            # Parsing for Selected and Current Program
            selected_program_match = re.search(r'Selected program: (.+?)\n', result.stdout)
            current_program_match = re.search(r'Program position: (.+?)\(', result.stdout)

            selected_program_full_path = selected_program_match.group(1).strip() if selected_program_match else "unknown"
            current_program_full_path = current_program_match.group(1).strip() if current_program_match else "unknown"

            # Extract only the filename from the full path
            selected_program = os.path.basename(selected_program_full_path)
            current_program = os.path.basename(current_program_full_path)

            # Continue with existing logic to parse execution line
            execution_line_match = re.search(r'Program position: .*\((\d+)\)', result.stdout)
            execution_line = int(execution_line_match.group(1)) if execution_line_match else 0

            return selected_program, current_program, execution_line
        except Exception as e:
            logging.error(f"Error in getCurrentProgramInfo: {e}")
            return "error_program", "error_program", 0

    def getMachineError(self):
        try:
            command_arguments = ["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address,
                                 "runinfo", "f"]
            result = self._run_command(command_arguments)
            logging.debug(f"Raw output for machine error: {result.stdout}")

            # Check for no errors present
            if "Error E20001739: No further errors present" in result.stdout:
                return "No Errors", "Regular"

            # Check for connection error
            if "Error E20001505: Cannot connect to the control" in result.stdout:
                return "Cannot connect to the control", "Connection Error"

            # Default case for unknown errors
            return "Unknown Error", "Unknown Class"
        except Exception as e:
            logging.error(f"An error occurred in getMachineError: {e}")
            # Return the exception message and a generic error class
            return str(e), "Exception"

    def emit_status_update(self, status_update):
        try:
            self.status_updated.emit(status_update)
            logging.info(f"Status updated: {status_update}")
        except Exception as e:
            self.status_updated.emit({
                'status': 'Error',
                'progress': 0,
                'selected_program': 'None',
                'current_program': 'None',
                'error_text': str(e),
                'error_class': 'Exception'
            })
            logging.error(f"An error occurred in emit_status_update: {str(e)}")

    if __name__ == "__main__":
        self.monitor = MachineMonitor("192.168.1.228", self.updateUI)
        self.monitor.status_updated.connect(self.updateUI)
        logging.info("MachineMonitor started in main.")  # Import necessary modules
