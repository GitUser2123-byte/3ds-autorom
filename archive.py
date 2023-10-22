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

ARCHIVE_IDENTIFIER = '3dscia_202310'
DESTINATION_PATH = os.path.join(os.getcwd(), 'output')  # Set the destination path to a subfolder called 'output'
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

    obj = SmartDL(url, output_path)
    obj.start(blocking=False)

    obj.wait()

    if obj.isSuccessful():
        print(f"Download of {file_name} complete!")

        # Create a directory for the extracted files
        extracted_folder_path = os.path.join(destination, os.path.splitext(file_name)[0])
        ensure_directory_exists(extracted_folder_path)

        if file_name.lower().endswith('.rar'):
            extract_rar(output_path, extracted_folder_path)
        elif file_name.lower().endswith('.zip'):
            extract_zip(output_path, extracted_folder_path)
        print(f"Extraction of {file_name} complete!")

        # Return the path of the extracted folder
        return extracted_folder_path
    else:
        print(f"Error during download: {obj.get_errors()}")
        return None

def delete_original_file(file_path):
    os.remove(file_path)

def move_to_usb(output_path, usb_device, destination_folder='', supported_extensions={'cia': '.cia', 'nds': '.nds'}):
    # Create the 'cia' and 'nds' folders on the root of the USB device
    destination_cia_path = os.path.join(usb_device, 'cia')
    destination_nds_path = os.path.join(usb_device, 'nds')
    ensure_directory_exists(destination_cia_path)
    ensure_directory_exists(destination_nds_path)

    if os.path.exists(output_path) and os.path.isdir(output_path):
        for file_name in os.listdir(output_path):
            base_name, file_extension = os.path.splitext(file_name)
            for folder_name, extension in supported_extensions.items():
                if file_extension.lower() == extension:
                    source_file_path = os.path.join(output_path, file_name)
                    destination_folder_path = os.path.join(usb_device, folder_name)
                    destination_file_path = os.path.join(destination_folder_path, file_name)
                    ensure_directory_exists(destination_folder_path)
                    shutil.move(source_file_path, destination_file_path)
        print(f"\nFiles moved to USB device: {usb_device}")
    else:
        print(f"Error: The path {output_path} does not exist or is not a directory.")


def list_connected_usb_devices():
    usb_devices = []
    for partition in psutil.disk_partitions():
        if 'removable' in partition.opts:
            usb_devices.append(partition.mountpoint)
    return usb_devices

def get_file_list(item_id):
    url = f'https://archive.org/metadata/{item_id}'
    response = requests.get(url)
    if response.status_code == 200:
        metadata = response.json()
        files = [file['name'] for file in metadata['files'] if file['name'] not in EXCLUDE_FILES]
        return files
    else:
        print(f"Failed to retrieve file list from {url}. Status code: {response.status_code}")
        return []

def main():
    file_list = get_file_list(ARCHIVE_IDENTIFIER)
    current_index = 0
    visible_range = (0, min(10, len(file_list)))

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        print("Archive Downloader")
        print("-------------------")
        print(f"\nCurrent Directory: {DESTINATION_PATH}\n")

        for i, file_name in enumerate(file_list[visible_range[0]:visible_range[1]]):
            marker = '*' if i + visible_range[0] == current_index else ' '
            print(f"{marker} {i + visible_range[0] + 1}. {file_name}")

        print("\nUse Arrow keys to navigate, 'Enter' to download, 'Q' to quit")

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
