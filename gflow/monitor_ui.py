# Add this import at the top of the file
import logging
import sys

from PyQt5.QtCore import QEvent
# The rest of your imports
from PyQt5.QtWidgets import QWidget

from db_manager import DBManager


class ControlWidget(QWidget):
    def __init__(self, main_ui, parent=None, row_id=None, update_table_callback=None):

        super().__init__(parent)
        min_height = 20  # You can adjust this value as needed
        self.setMinimumHeight(min_height)
        self.main_ui = main_ui  # Reference to MonitorUI instance
        self.row_id = row_id
        self.update_table_callback = update_table_callback

        layout = QHBoxLayout(self)
        # layout.addStretch()
        self.manual_upload_button = QPushButton("Manual Upload", self)
        # layout.addStretch()
        self.start_program_button = QPushButton("Start Program", self)
        # layout.addStretch()
        self.delete_button = QPushButton("X", self)

        # Style the start button
        # self.start_program_button.setAlignment(Qt.AlignCenter)
        # self.manual_upload_button.setAlignment(Qt.AlignCenter)

        # Style the delete button
        self.delete_button.setStyleSheet("background-color: red; border-radius: 10px;")
        self.delete_button.setFixedSize(20, 20)  # Set fixed size to 30x30

        self.manual_upload_button.setMinimumHeight(min_height)
        self.start_program_button.setMinimumHeight(min_height)
        self.delete_button.setMinimumHeight(min_height)
        self.manual_upload_button.clicked.connect(self.manual_upload)
        self.start_program_button.clicked.connect(self.start_program)
        self.delete_button.clicked.connect(self.delete_entry)  # Connect the delete button

        layout.addWidget(self.manual_upload_button)
        layout.addWidget(self.start_program_button)
        layout.addWidget(self.delete_button)
        self.setLayout(layout)

    def remove_entry_from_database(self):

        new_data = []
        with open("DATABASE/database.txt", "r") as file:
            for line in file:
                program_id, _, _, _, _ = line.strip().split(',')
                if program_id != self.row_id:
                    new_data.append(line)

        with open("DATABASE/database.txt", "w") as file:
            file.writelines(new_data)

    def delete_entry(self):

        confirm_msg = QMessageBox()
        confirm_msg.setIcon(QMessageBox.Warning)
        confirm_msg.setText("Are you sure you want to delete this entry?")
        confirm_msg.setWindowTitle("Confirm Deletion")
        confirm_msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        choice = confirm_msg.exec_()
        if choice == QMessageBox.Yes:
            self.remove_entry_from_database()
            if self.update_table_callback:
                self.update_table_callback()

    @staticmethod
    def get_program_name_from_db(row_id):

        db_file = os.path.join(os.path.dirname(__file__), 'DATABASE', 'database.txt')
        with open(db_file, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    program_id, _, program_name, _, _, _ = parts
                    if str(program_id) == str(row_id):
                        return program_name
        return None

    def manual_upload(self):

        logging.debug(f"Initiating manual upload for row ID {self.row_id}")
        try:
            program_name = ControlWidget.get_program_name_from_db(self.row_id)
            if program_name:
                file_path = os.path.join("C:\\AUTO\\NIGHT", program_name)
                logging.debug(f"Attempting to upload file: {file_path}")
                upload_success = self.upload_file(file_path, self.main_ui.monitor.ip_address)

                if upload_success:
                    self.manual_upload_button.setText("Uploaded")
                    self.manual_upload_button.setStyleSheet("background-color: green;")
                    self.main_ui.update_database(self.row_id, "Uploaded")  # Update the database entry
                    self.main_ui.update_status_in_table(self.row_id, "Uploaded")  # Update the UI status
                else:
                    logging.debug("Upload failed, could not update the status.")
            else:
                logging.debug(f"No program found for row ID {self.row_id}")
        except Exception as e:
            logging.error(f"Exception occurred during manual upload: {e}")

    def upload_file(self, file_path, machine_ip):

        logging.debug(f"Starting file upload: {file_path} to machine IP: {machine_ip}")
        try:
            file_name = os.path.basename(file_path)
            tnc_cmd = "C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe"
            result = subprocess.run([tnc_cmd, "-i", machine_ip, f"PUT {file_path} TNC:\\camflow\\{file_name} /o"],
                                    capture_output=True, text=True)

            if result.returncode == 0:
                logging.debug(f"File successfully uploaded: {file_path}")
                return True
            else:
                logging.error(f"Error during file upload: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Exception occurred during file upload: {e}")
            return False

    def update_status_in_table(self, row_id, status):
        try:
            row_index = self.find_row_index_by_id(row_id)
            if row_index is not None:
                status_column_index = 6  # "Status" column index
                self.table.item(row_index, status_column_index).setText(status)
                self.table.item(row_index, status_column_index).setBackground(
                    QColor('green'))  # Set text color to green
                self.table.viewport().update()  # Refresh the table
        except Exception as e:
            logging.error(f"UI Update Error: {e}")
            print(f"Error updating status in table: {e}")

    def find_row_index_by_id(self, row_id):
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).text() == row_id:
                return i
        return None

    def start_program(self):
        # Logic to start a program
        pass


class QStatusEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, row_id, status):
        super().__init__(QStatusEvent.EVENT_TYPE)
        self.row_id = row_id
        self.status = status


# Import necessary modules
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTableWidget, \
    QPushButton, QTableWidgetItem, QHeaderView, QDialog, QMessageBox
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtGui import QFont
from machine_monitor import MachineMonitor
from datetime import datetime, timedelta
import os
import subprocess


class MonitorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.update_ui_with_database_data()
        # Initialize MachineMonitor
        self.monitor = MachineMonitor("192.168.1.228", self.updateUI)
        self.monitor.status_updated.connect(self.update_status)

    def initUI(self):
        self.setWindowTitle("HSM 200 U LP GFlow")
        self.setGeometry(100, 100, 1200, 800)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui_with_database_data)
        self.update_timer.start(10000)  # Update every 10 seconds

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)

        # Upper Section
        self.initUpperSection(main_layout)

        # Middle Section
        self.initMiddleSection(main_layout)

        # Bottom Section with additional "Cancel Error" button
        self.initBottomSection(main_layout)

        # Apply bold font to labels and buttons
        bold_font = QFont()
        bold_font.setBold(True)

        self.line_number_label.setFont(bold_font)
        self.machine_status_label.setFont(bold_font)
        self.selected_program_label.setFont(bold_font)
        self.current_program_label.setFont(bold_font)
        self.auto_button.setFont(bold_font)
        self.sleep_button.setFont(bold_font)
        self.cancel_error_button.setFont(bold_font)

        # Start the monitor
        self.monitor = MachineMonitor("192.168.1.228", self.updateUI)
        # self.monitor.start()

    def update_status(self, status, progress, selected_program, current_program, error_text, error_class):
        # Update the UI based on the status
        self.update_machine_status(status)
        self.update_line_number(progress)
        self.update_selected_program(selected_program)
        self.update_current_program(current_program)
        self.update_error_label(error_text, error_class)

    def setMonitor(self, machine_monitor):
        self.machine_monitor = machine_monitor

    def update_error_label(self, error_text, error_class):
        if error_text == "No Errors":
            self.error_label.setText(error_text)
            self.error_label.setStyleSheet("color: black;")  # Regular text color
        else:
            self.error_label.setText(f"Error: {error_text}, Class: {error_class}")
            self.error_label.setStyleSheet("color: red;")  # Red text color for errors

    def customEvent(self, event):
        if event.type() == QStatusEvent.EVENT_TYPE:
            self.update_status_in_table(event.row_id, event.status)

    def update_status_in_table(self, row_id, status):
        try:
            row_index = self.find_row_index_by_id(row_id)
            if row_index is not None:
                status_column_index = 6  # "Status" column index
                self.table.item(row_index, status_column_index).setText(status)
                self.table.item(row_index, status_column_index).setBackground(
                    QColor('green'))  # Set text color to green
                self.table.viewport().update()  # Refresh the table
        except Exception as e:
            logging.error(f"UI Update Error: {e}")
            print(f"Error updating status in table: {e}")

    def update_database(self, row_id, status):
        db_manager = DBManager()
        if db_manager.connect():
            db_manager.update_status(row_id, status)  # Assuming you have a method to update status
            db_manager.disconnect()
            self.update_ui_with_database_data()  # Update the UI with the new data



    def update_ui_with_database_data(self):
        print("Inside update_ui_with_database_data")
        # Clear the existing contents of the table
        self.table.clearContents()

        # Create an instance of DBManager and fetch data from the MySQL database
        db_manager = DBManager()
        if db_manager.connect():
            data = db_manager.fetch_data()  # Fetch data from the MySQL database
            db_manager.disconnect()
        else:
            data = []
            print("Failed to connect to the database.")

        # Set the number of rows in the table based on the data length
        self.table.setRowCount(len(data))

        # Iterate over each entry in the data and update the table
        for row_index, entry in enumerate(data):
            # Assuming entry is a tuple or list in the order of your MySQL table columns
            # Create a ControlWidget for each row
            control_widget = ControlWidget(self, row_id=entry[0],  # Assuming program_id is the first column
                                           update_table_callback=self.update_ui_with_database_data)

            # Handle different total_runtime formats
            total_runtime = entry[3]  # Adjust the index based on your table structure
            minutes, seconds = (total_runtime.split(':') if ':' in total_runtime else
                                (total_runtime, '0') if total_runtime.isdigit() else ('0', '0'))

            total_minutes = int(minutes) + int(seconds) // 60
            completion_time_str = self.minutes_to_hours(str(total_minutes))

            # Set the row height and populate the table cells
            self.table.setRowHeight(row_index, 20)
            self.table.setCellWidget(row_index, 6, control_widget)  # Assuming control widgets are in the 7th column
            self.table.setItem(row_index, 0, QTableWidgetItem(entry['program_id']))
            self.table.setItem(row_index, 1, QTableWidgetItem(entry['pallet_number']))
            self.table.setItem(row_index, 2, QTableWidgetItem(entry['program_name']))
            self.table.setItem(row_index, 3, QTableWidgetItem(entry['creation_time']))
            self.table.setItem(row_index, 4, QTableWidgetItem(completion_time_str))
            self.table.setItem(row_index, 5, QTableWidgetItem(entry['status']))  # Assuming status is in the 6th column

        # Update the completion time
        self.updateCompletionTime()



        # Constants section

    def updateCompletionTime(self):
        total_milling_time = timedelta()
        current_time = datetime.now()

        for row in range(self.table.rowCount()):
            milling_time_str = self.table.item(row, 4).text() if self.table.item(row, 4) else "0:00"
            hours, minutes = map(int, milling_time_str.split(':'))
            milling_time_delta = timedelta(hours=hours, minutes=minutes)
            total_milling_time += milling_time_delta

        estimated_completion = current_time + total_milling_time
        self.completion_time_label.setText(f"Estimated Completion: {estimated_completion.strftime('%Y-%m-%d %H:%M')}")

    def closeEvent(self, event):
        # Properly stop the thread
        self.monitor.thread.quit()
        self.monitor.thread.wait()
        super().closeEvent(event)

    # Constants section
    STATUS_AUTOMATIC = "Automatic"
    STATUS_LABEL_TEXT = "Machine Status: "
    LINE_NUMBER_LABEL_TEXT = "Line Number: "
    SELECTED_PROGRAM_LABEL_TEXT = "Selected Program: "
    CURRENT_PROGRAM_LABEL_TEXT = "Current Program: "
    ERROR_LABEL_NO_ERRORS_TEXT = "No Errors"
    ERROR_STYLESHEET_RED = "color: red;"
    ERROR_STYLESHEET_BLACK = "color: black;"

    @pyqtSlot(str, int, str, str, str, str)
    def updateUI(self, status, progress, selected_program, current_program, error_text, error_class):
        self.update_machine_status(status)
        self.update_line_number(progress)
        self.update_selected_program(selected_program)
        self.update_current_program(current_program)
        self.update_error_label(error_text, error_class)
        logging.info(f"UI Updated: {error_text}, Class: {error_class}")

    def update_machine_status(self, status):
        status_html = f"<span style='color: green; font-weight: normal;'>{status}</span>" if status == STATUS_AUTOMATIC else status
        self.machine_status_label.setText(f"{STATUS_LABEL_TEXT}{status_html}")




    def update_line_number(self, progress):
        self.line_number_label.setText(
            f"{LINE_NUMBER_LABEL_TEXT}<span style='font-weight: normal; color: black;'>{progress}</span>")


    def update_selected_program(self, selected_program):
        self.selected_program_label.setText(
            f"{SELECTED_PROGRAM_LABEL_TEXT}<span style='font-weight: normal; color: black;'>{selected_program}</span>")


    def update_current_program(self, current_program):
        self.current_program_label.setText(
            f"{CURRENT_PROGRAM_LABEL_TEXT}<span style='font-weight: normal; color: black;'>{current_program}</span>")


    def update_error_label(self, error_text, error_class):
        if error_text and error_class:
            self.error_label.setText(f"Error: {error_text}, Class: {error_class}")
            self.error_label.setStyleSheet(ERROR_STYLESHEET_RED)
        elif error_text:
            self.error_label.setText(error_text)
            self.error_label.setStyleSheet(ERROR_STYLESHEET_RED)
        else:
            self.error_label.setText(ERROR_LABEL_NO_ERRORS_TEXT)
            self.error_label.setStyleSheet(ERROR_STYLESHEET_BLACK)



    def initUpperSection(self, layout):
        upper_layout = QHBoxLayout()

        self.line_number_label = QLabel("Line Number: --", self)
        upper_layout.addWidget(self.line_number_label)

        self.machine_status_label = QLabel("Machine Status: Unknown", self)
        upper_layout.addWidget(self.machine_status_label)

        self.selected_program_label = QLabel("Selected Program: None", self)
        upper_layout.addWidget(self.selected_program_label)

        self.current_program_label = QLabel("Current Program: None", self)
        upper_layout.addWidget(self.current_program_label)

        self.live_screen_button = QPushButton("Live Screen", self)
        upper_layout.addWidget(self.live_screen_button)
        self.live_screen_button.clicked.connect(self.show_live_screen)

        self.error_label = QLabel("Error: None", self)
        self.error_label.setStyleSheet("color: red;")
        upper_layout.addWidget(self.error_label)

        layout.addLayout(upper_layout)

    def initMiddleSection(self, layout):
        self.table = QTableWidget(self)
        self.table.setColumnCount(8)  # Number of columns
        self.table.setHorizontalHeaderLabels(
            ["ID", "Pallet", "Program", "Created", "Milling Time", "Control", "Status", "ATP Program"])
        layout.addWidget(self.table)

        # Set column widths to be resizable
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # "Program" column
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # "Control" column
        # When populating the table
        # data = self.read_database()
        # for row_index, entry in enumerate(data):
        #    control_widget = ControlWidget(parent=self, row_id=entry['program_id'], update_table_callback=self.update_ui_with_database_data)
        #    self.table.setCellWidget(row_index, 5, control_widget)  # Ensure correct column index

        # Set row heights to be adjustable based on content
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.completion_time_label = QLabel("Estimated Completion: --", self)
        layout.addWidget(self.completion_time_label)

    def initBottomSection(self, layout):
        bottom_layout = QHBoxLayout()

        self.auto_button = QPushButton("AUTO", self)
        bottom_layout.addWidget(self.auto_button)

        self.sleep_button = QPushButton("SLEEP", self)
        bottom_layout.addWidget(self.sleep_button)

        # Adding the "Cancel Error" button
        self.cancel_error_button = QPushButton("Cancel Error", self)
        bottom_layout.addWidget(self.cancel_error_button)
        self.cancel_error_button.clicked.connect(self.cancel_error)

        layout.addLayout(bottom_layout)

    def cancel_error(self):
        # Send CE with KEY command to the machine
        try:
            result = subprocess.run(
                ["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.monitor.ip_address, "KEY",
                 "CE"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # You may want to update the UI to reflect the error has been cancelled
                self.error_label.setText("No Errors")
                self.error_label.setStyleSheet("color: green;")
                logging.info("Error cancelled successfully.")
            else:
                logging.error("Failed to cancel error on the machine.")
        except Exception as e:
            logging.error(f"Error cancelling error on the machine: {e}")

    def show_live_screen(self):
        screen_file_path = self.fetch_live_screen()
        if screen_file_path:
            self.display_live_screen(screen_file_path)
            os.remove(screen_file_path)  # Clean up the temporary file

    def fetch_live_screen(self):
        temp_bitmap_file = "\\temp\\temp.bmp"
        try:
            subprocess.run(
                ["C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe", "-i", self.monitor.ip_address,
                 "screen", temp_bitmap_file], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if os.path.exists(temp_bitmap_file):
                return temp_bitmap_file
            else:
                print("Failed to fetch or save live screen.")
                return None
        except Exception as e:
            logging.error(f"UI Update Error: {e}")
            print(f"Error in fetching live screen: {e}")
            return None

    def display_live_screen(self, screen_file_path):
        dialog = QDialog(self)
        dialog.setWindowTitle("Live Screen")
        layout = QVBoxLayout(dialog)

        pixmap = QPixmap(screen_file_path)
        label = QLabel(dialog)
        label.setPixmap(pixmap)
        layout.addWidget(label)

        dialog.exec_()

    def updateUI(self, status, progress, program_name=None, error_text=None, error_class=None):
        # Emit the signal with the new data
        # print(f"Emitting signal: status={status}, line={current_line}, program={current_program}")
        self.status_updated.emit(status, progress, program_name, error_text, error_class)
        if program_name:
            self.current_program_label.setText(f"Current Program: {program_name}")
            self.current_program_label.repaint()
        else:
            self.current_program_label.setText("Current Program: None")
            self.current_program_label.repaint()

        # Update the machine status label
        self.machine_status_label.setText(f"Machine Status: {status}")

        # Update the line number label with the progress (line number)
        self.line_number_label.setText(f"Line Number: {progress}")

        # Update the error information
        if error_text and error_class:
            self.error_label.setText(f"Error: {error_text}, Class: {error_class}")
        else:
            self.error_label.setText("No Errors")



    @staticmethod
    def minutes_to_hours(minutes_str):
        total_minutes = int(minutes_str)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def fetch_data_from_database(self):
        # Create an instance of DBManager
        db_manager = DBManager()

        # Connect to the database and fetch data
        data = []
        try:
            if db_manager.connect():
                data = db_manager.fetch_all_data()  # Fetch all data from the MySQL database
                db_manager.disconnect()
            else:
                print("Failed to connect to the database.")
        except Exception as e:
            print(f"Error fetching data from database: {e}")

        return data





    def update_callback(self, status, progress, program_name=None, error_text=None, error_class=None):
        # Update the UI elements with the received data
        self.machine_status_label.setText(f"Machine Status: {status}")
        self.line_number_label.setText(f"Line Number: {progress}")
        self.current_program_label.setText(f"Current Program: {program_name or 'None'}")
        self.current_program_label.repaint()
        if error_text and error_class:
            self.error_label.setText(f"Error: {error_text}, Class: {error_class}")
        else:
            self.error_label.setText("No Errors")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MonitorUI()
    main_window.show()
    sys.exit(app.exec_())
