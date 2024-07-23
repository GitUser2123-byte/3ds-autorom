import os
import subprocess
import platform
import requests
import msvcrt
from pySmartDL import SmartDL
from rarfile import RarFile
import zipfile
import shutil
import psutil
import ssl
import urllib.request

ARCHIVE_IDENTIFIER = '3dscia_202310'
DESTINATION_PATH = os.path.join(os.getcwd(), 'output')
EXCLUDE_FILES = ['3dscia_202310_archive.torrent', '3dscia_202310_files.xml', '3dscia_202310_meta.sqlite', '3dscia_202310_meta.xml']

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def extract_rar(file_path, destination):
    with RarFile(file_path, 'r') as rar:
        rar.extractall(destination)

def extract_zip(file_path, destination):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(destination)

def download_file(item_id, file_name, destination):
    url = f'https://archive.org/download/{item_id}/{file_name}'

    ensure_directory_exists(destination)

    output_path = os.path.join(destination, file_name)

    context = ssl._create_unverified_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    urllib.request.install_opener(opener)

    obj = SmartDL(url, output_path, threads=4)
    obj.start(blocking=False)

    obj.wait()

    if obj.isSuccessful():
        print(f"Download of {file_name} complete!")

        extracted_folder_path = os.path.join(destination, os.path.splitext(file_name)[0])
        ensure_directory_exists(extracted_folder_path)

        if file_name.lower().endswith('.rar'):
            extract_rar(output_path, extracted_folder_path)
        elif file_name.lower().endswith('.zip'):
            extract_zip(output_path, extracted_folder_path)
        print(f"Extraction of {file_name} complete!")

        return extracted_folder_path
    else:
        print(f"Error during download: {obj.get_errors()}")
        return None

def delete_original_file(file_path):
    os.remove(file_path)

def move_to_usb(output_path, usb_device):
    for root, dirs, files in os.walk(output_path):
        for file in files:
            if file.lower().endswith('.cia'):
                target_dir = os.path.join(usb_device, 'cia')
            elif file.lower().endswith('.nds'):
                target_dir = os.path.join(usb_device, 'nds')
            else:
                continue

            ensure_directory_exists(target_dir)
            shutil.move(os.path.join(root, file), os.path.join(target_dir, file))
            print(f"Moved {file} to {target_dir}")

def list_connected_usb_devices():
    usb_devices = []
    if platform.system() == 'Windows':
        for partition in psutil.disk_partitions():
            if 'removable' in partition.opts:
                usb_devices.append(partition.device)
    elif platform.system() == 'Linux':
        result = subprocess.run(['lsblk', '-o', 'NAME,MOUNTPOINT'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if '/media' in line:
                usb_devices.append(line.split()[0])
    return usb_devices

def get_file_list():
    response = requests.get(f'https://archive.org/download/{ARCHIVE_IDENTIFIER}/{ARCHIVE_IDENTIFIER}_files.xml')
    file_list = []
    if response.status_code == 200:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)
        for file_elem in root.findall(".//file"):
            file_name = file_elem.get("name")
            if file_name and file_name.endswith(('.rar', '.zip')) and file_name not in EXCLUDE_FILES:
                file_list.append(file_name)
    else:
        print(f"Failed to retrieve file list. Status code: {response.status_code}")
    return file_list

def main():
    file_list = get_file_list()

    if not file_list:
        print("No .rar or .zip files found.")
        return

    current_index = 0
    visible_range = (0, min(len(file_list), 10))

    while True:
        os.system('cls' if platform.system() == 'Windows' else 'clear')
        print("3DS Archive Downloader")
        print("======================")
        for i, file_name in enumerate(file_list[visible_range[0]:visible_range[1]]):
            prefix = '>' if i + visible_range[0] == current_index else ' '
            print(f"{prefix} {file_name}")

        print("\nUse arrow keys to navigate, Enter to select, q to quit.")

        key = ''
        if platform.system() == 'Windows':
            key = msvcrt.getch().decode('utf-8', errors='ignore')
        else:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                key = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        if key == 'q':
            break
        elif key == '\r':
            file_name = file_list[current_index]
            file_destination = os.path.join(DESTINATION_PATH, file_name)
            extracted_folder_path = download_file(ARCHIVE_IDENTIFIER, file_name, DESTINATION_PATH)

            if extracted_folder_path:
                delete_original_file(file_destination)

                usb_devices = list_connected_usb_devices()
                if usb_devices:
                    print("\nConnected USB Devices:")
                    for i, device in enumerate(usb_devices):
                        print(f"{i + 1}. {device}")

                    selected_device_index = int(input("Select a USB device (enter the corresponding number): ")) - 1
                    selected_usb_device = usb_devices[selected_device_index]

                    move_to_usb(extracted_folder_path, selected_usb_device)
                else:
                    print("\nNo connected USB devices found.")

                input("\nPress Enter to continue.")
        elif key == 'H':
            current_index = (current_index - 1) % len(file_list)
            if current_index < visible_range[0]:
                visible_range = (max(0, visible_range[0] - 1), visible_range[1] - 1)
        elif key == 'P':
            current_index = (current_index + 1) % len(file_list)
            if current_index >= visible_range[1]:
                visible_range = (visible_range[0] + 1, min(len(file_list), visible_range[1] + 1))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
