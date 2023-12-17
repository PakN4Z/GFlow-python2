import logging
import os
import time
import shutil
import subprocess
from tkinter import messagebox, Tk, Button, Label, Toplevel, StringVar, Entry
import datetime
from datetime import datetime
import xml.etree.ElementTree as ET
import re
from db_manager import DBManager

# Directories to monitor
directories = {
    "V:\\machines\\4": "192.168.1.228",
    "V:\\machines\\2": "192.168.1.230"
}

def show_custom_dialog(file_name, root):
    print(f"Bandau rodyti pranešimą apie failą: {file_name}")

    dialog = Toplevel(root)
    dialog.title("Rasta nauja programa")
    Label(dialog, text=f"Rasta nauja programa: {file_name}\nPasirinkite veiksmą").pack()

    response = {"value": None}

    def set_response_and_close(res):
        response["value"] = res
        dialog.destroy()

    Button(dialog, text="Įkelti ATP", command=lambda: set_response_and_close("Įkelti ATP")).pack()
    Button(dialog, text="Įkelti TAISOM", command=lambda: set_response_and_close("Įkelti TAISOM")).pack()
    Button(dialog, text="Įsivesk pats", command=lambda: set_response_and_close("Įsivesk pats")).pack()
    Button(dialog, text="Siųsti naktiniam procesui", command=lambda: set_response_and_close("Siųsti naktiniam procesui")).pack()
    Button(dialog, text="Ignoruoti", command=lambda: set_response_and_close("Ignoruoti")).pack()

    root.wait_window(dialog)

    print(f"Dialogas uždarytas su pasirinkimu: {response['value']}")
    return response["value"]

def process_file(file_path, machine_ip, action, root):
    try:
        file_name = os.path.basename(file_path)
        pallet_number = extract_pallet_number(file_name)

        # Assuming you have an XML file with the same name but different extension in the same directory
        xml_file_path = file_path.replace('.h', '.xml')
        creation_time, total_runtime = parse_xml_file(xml_file_path)

        # Use 'total_runtime' as needed. If you were using 'total_time' for logging, replace it with 'total_runtime'
        update_log(file_name, machine_ip, action, total_runtime)
        print(f"Apdorojamas failas: {file_name}, Veiksmas: {action}")
        print(f"Apdorojamas failas: {file_name}, Veiksmas: {action}")

        if action == "Įkelti ATP":
            new_file_name = f"ATP_{pallet_number}_VIETA_{get_time_stamp()}.h"
            modify_and_upload(file_path, new_file_name, machine_ip, pallet_number)
        elif action == "Įkelti TAISOM":
            new_file_name = f"TAISOM_{pallet_number}_VIETA_{get_time_stamp()}.h"
            modify_and_upload(file_path, new_file_name, machine_ip, pallet_number)
        elif action == "Siųsti naktiniam procesui":
            process_for_night_folder(file_path, machine_ip)
            messagebox.showinfo("Sėkmė", "Failas nusiųstas naktiniam procesui")
        elif action == "Įsivesk pats":
            additional_symbols = get_user_input(root)
            new_file_name = f"{additional_symbols}_TAISOM_{pallet_number}_VIETA_{get_time_stamp()}.h"
            modify_and_upload(file_path, new_file_name, machine_ip, pallet_number)

    except Exception as e:
        logging.error(f"UI Update Error: {e}")
        messagebox.showerror("Klaida", f"Įvyko klaida: {e}")

from db_manager import DBManager

def process_for_night_folder(file_path, machine_ip):
    night_folder = "NIGHT" if machine_ip == "192.168.1.228" else "NIGHT2"
    night_folder_path = os.path.join("C:\\AUTO", night_folder)
    shutil.copy(file_path, night_folder_path)

    file_name = os.path.basename(file_path)
    pallet_number = extract_pallet_number(file_name)
    
    # New: Create an instance of DBManager and add an entry to the database
    db_manager = DBManager()
    if db_manager.connect():
        db_manager.insert_data(pallet_number, os.path.basename(file_path), 
                               datetime.now().strftime('%Y-%m-%d %H:%M'), '0')  # Assuming '0' for total_runtime
        db_manager.disconnect()

    # Rename file to remove unwanted symbols
    file_name = os.path.basename(file_path)
    new_file_name = re.sub(r"[ \[\]]", "_", file_name)
    temp_file = os.path.join(night_folder_path, new_file_name)
    os.rename(os.path.join(night_folder_path, file_name), temp_file)

    # Modify file contents if pallet number is less than 15
    pallet_number = extract_pallet_number(new_file_name)
    with open(temp_file, 'r') as file:
        lines = file.readlines()

    if int(pallet_number) < 15:
        lines.insert(1, f"CYCL DEF 320 Pallet Change ~\nQ398=+{pallet_number}    ;Pallet number ~\nQ399=+2    ;Chuck number\nCYCL DEF 247 PRESETTING ~\nQ339=+{pallet_number}   ;PRESET NUMBER\n")

    with open(temp_file, 'w') as file:
        file.writelines(lines)

    # Copy and rename XML file
    xml_file_name = file_name.replace('.h', '.xml')
    xml_file_path = os.path.join("V:\\machines\\4" if machine_ip == "192.168.1.228" else "V:\\machines\\2", xml_file_name)
    shutil.copy(xml_file_path, night_folder_path)
    new_xml_file_name = re.sub(r"[ \[\]]", "_", xml_file_name)
    os.rename(os.path.join(night_folder_path, xml_file_name), os.path.join(night_folder_path, new_xml_file_name))

    # Process the copied files
    process_copied_files(temp_file, os.path.join(night_folder_path, new_xml_file_name))

def process_copied_files(h_file, xml_file):
    try:
        pallet_number = extract_pallet_number(os.path.basename(h_file))
        creation_time, total_runtime = parse_xml_file(xml_file)
        
        # Create an instance of the DatabaseManager
        db_manager = DBManager()
        if db_manager.connect():
            db_manager.insert_data(pallet_number, os.path.basename(h_file), 
                                   creation_time.strftime('%Y-%m-%d %H:%M'), total_runtime)
            db_manager.disconnect()

    except Exception as e:
        logging.error(f"UI Update Error: {e}")
        print(f"Error in process_copied_files: {e}")
        
def auto_generate_program_id(db_manager: DBManager) -> int:
    if db_manager.connect():
        last_id = db_manager.get_last_program_id()
        db_manager.disconnect()
        return last_id + 1 if last_id else 1        

def parse_xml_file(xml_file):
    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"XML file not found: {xml_file}")

    tree = ET.parse(xml_file)
    root = tree.getroot()

    date = root.find('.//file/date').text
    time = root.find('.//file/time').text
    creation_time = datetime.strptime(f"{date} {time}", "%Y/%m/%d %H:%M")

    total_runtime = root.find('.//statistic/TotalTime').text
    return creation_time, total_runtime





def extract_pallet_number(file_name):
    try:
        # Adjust this pattern according to your file naming convention
        match = re.search(r"(\d+)-\d+-\d+_\d+", file_name)
        if match:
            return match.group(1)
        else:
            raise ValueError("Pallet number not found in file name.")
    except IndexError:
        raise ValueError("Incorrect file name format.")

def get_time_stamp():
    now = datetime.datetime.now()
    return f"{now.hour:02d}_{now.minute:02d}"

def modify_and_upload(original_file, new_file_name, machine_ip, pallet_number):
    try:
        print(f"Modifikuojamas ir siunčiamas failas: {new_file_name}")
        temp_file = f"C:\\AUTO\\TEMP\\{new_file_name}"
        with open(original_file, 'r') as file:
            lines = file.readlines()

        if int(pallet_number) < 15:
            lines.insert(1, f"CYCL DEF 320 Pallet Change ~\nQ398=+{pallet_number}    ;Pallet number ~\nQ399=+2    ;Chuck number\nCYCL DEF 247 PRESETTING ~\nQ339=+{pallet_number}   ;PRESET NUMBER\n")

        with open(temp_file, 'w') as file:
            file.writelines(lines)

        tnc_cmd = f"C:\\Program Files (x86)\\HEIDENHAIN\\TNCremo\\TNCcmdPlus.exe"
        subprocess.run([tnc_cmd, "-i", machine_ip, f"PUT {temp_file} TNC:\\camflow\\{new_file_name} /o"])
        messagebox.showinfo("Sėkmė", "Failai sėkmingai nusiųsti")

        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"Laikinas failas {temp_file} ištrintas")

    except Exception as e:
        logging.error(f"UI Update Error: {e}")
        messagebox.showerror("Klaida", f"Įvyko klaida apdorojant failą: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"Laikinas failas {temp_file} ištrintas dėl klaidos")

def get_user_input(root):
    input_dialog = Toplevel(root)
    input_dialog.title("Įveskite papildomus simbolius")
    Label(input_dialog, text="Įveskite papildomus simbolius:").pack()

    input_var = StringVar()
    entry = Entry(input_dialog, textvariable=input_var)
    entry.pack()

    def submit_and_close():
        input_dialog.destroy()

    Button(input_dialog, text="Pateikti", command=submit_and_close).pack()
    root.wait_window(input_dialog)
    return input_var.get()

def update_log(file_name, machine_ip, action, total_time):
    log_entry = f"{datetime.now()}, {file_name}, {machine_ip}, {action}, {total_time}\n"
    with open("log.txt", "a") as log_file:
        log_file   

def monitor_directories():
    known_files = {dir: set(os.listdir(dir)) for dir in directories}
    root = Tk()
    root.withdraw()

    while True:
        for dir, ip in directories.items():
            current_files = set(os.listdir(dir))
            current_h_files = {file for file in current_files if file.endswith('.h')}
            known_h_files = known_files[dir]
            new_files = current_h_files - known_h_files
            if new_files:
                print(f"Nauji .h failai aptikti kataloge {dir}: {new_files}")

            for file in new_files:
                file_path = os.path.join(dir, file)
                response = show_custom_dialog(file, root)
                if response and response != 'Ignoruoti':
                    process_file(file_path, ip, response, root)

            known_files[dir] = current_h_files
        time.sleep(1)

if __name__ == "__main__":
    print("Pradedamas katalogų stebėjimas...")
    monitor_directories()