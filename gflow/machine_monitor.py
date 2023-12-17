# Import necessary modules
import logging
import subprocess
import time
import os
import re
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from db_manager import DBManager

class MachineMonitor(QObject):
    status_updated = pyqtSignal(str, int, str, str, str, str)

    def fetch_data_from_database(self):
        """
        Fetches data from the database and returns it.
        """
        db_manager = DBManager()
        data = []
        if db_manager.connect():
            data = db_manager.fetch_data()  # Fetch data from the MySQL database
            db_manager.disconnect()
        else:
            print("Failed to connect to the database.")
        return data
    
    def startMonitoring(self):
        if not self.thread:
            self.thread = QThread()
            self.moveToThread(self.thread)
            self.thread.started.connect(self.run)
            self.running = True
            self.thread.start()

    def stopMonitoring(self):
        self.running = False
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
            self.thread = None  # Reset the thread

    def __init__(self, ip_address, update_callback=None):

        super().__init__()
        self.ip_address = ip_address
        self.update_callback = update_callback
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.run)
        self.running = True
        self.db_manager = DBManager()
        self.thread.start()  

    def run(self):

        self.connect_to_machine()
        while self.running:
            try:
                # Your logic to get status, program info, etc.
                status = self.getMachineStatus()
                selected_program, current_program, current_line = self.getCurrentProgramInfo()
                error_text, error_class = self.getMachineError()

                if self.update_callback:
                    self.update_callback(status, current_line, selected_program, current_program, error_text,
                                         error_class)
            
            except Exception as e:
                logging.exception("An error occurred in the run method.")
                if self.update_callback:
                    # Call update_callback with error information
                    self.update_callback('Error', 0, 'None', 'None', str(e), 'Exception')
            
            time.sleep(10)  # Adjust the sleep time as needed

        self.close_connection()

    def stop(self):

        self.running = False
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    

    

    def connect_to_machine(self):

        # Code to establish a connection to the machine
        # This is a placeholder. You need to replace it with actual code to open a persistent connection.
        self.process = subprocess.Popen(["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def reconnect_to_machine(self):

        # Attempt to re-establish the connection
        self.close_connection()
        self.connect_to_machine()

    def close_connection(self):

        # Code to gracefully close the connection
        if self.process:
            self.process.terminate()
            self.process = None

    def getMachineStatus(self):

        try:
            result = subprocess.run(["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address, "runinfo", "e"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
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
            # Construct the path to the NIGHT folder relative to the script directory
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
            result = subprocess.run(
                ["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address, "runinfo", "p"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
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
            result = subprocess.run(
                ["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.ip_address, "runinfo", "f"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
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

    @staticmethod


    def update_callback(self, *args, **kwargs):
        # Emit the signal with up to six arguments
        self.status_updated.emit(*args[:6])


        # Limit the number of arguments to six
        args = args[:6]
        if self.update_callback:
            self.update_callback(*args)
        
        # Additional logging for debugging
        if len(args) > 0:
            print(f"Status: {args[0]}")
        
        # Example of handling and printing the arguments for debugging or logging
        if len(args) > 0:
            print(f"Status: {args[0]}")
        if len(args) > 1:
            print(f"Progress: {args[1]}%")
        if len(args) > 2:
            print(f"Selected Program: {args[2]}")
        if len(args) > 3:
            print(f"Current Program: {args[3]}")
        if len(args) > 4:
            print(f"Error Text: {args[4]}")
        if len(args) > 5:
            print(f"Error Class: {args[5]}")

if __name__ == "__main__":
    def example_update_callback(*args, **kwargs):

        print(f"Received callback with arguments: {args}")

    monitor = MachineMonitor("192.168.1.228", example_update_callback)
    #monitor.start()