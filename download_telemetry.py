import requests
import zipfile
import io
import os
import shutil


# Configuration
API_URL = 'https://ktvincco.com/services/universal_telemetry/download_telemetry.php'
TELEMETRY_DIR = "collected_telemetry"
API_KEY_FILE = "private/api_key.txt"


# Read API key
with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
    API_KEY = f.read().strip()


def fetch_and_unpack():

    # Check API_KEY file
    if not os.path.isfile(API_KEY_FILE):
        print(f"Error {API_KEY_FILE} do not exist")
        return

    # POST the key and fetch the zip
    resp = requests.post(API_URL, data={'api_key': API_KEY}, stream=True)
    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        return

    # Ensure destination folder exists, overwrite any existing files
    if os.path.isdir(TELEMETRY_DIR):
        shutil.rmtree(TELEMETRY_DIR)
    os.makedirs(TELEMETRY_DIR, exist_ok=True)

    # Read response content into a BytesIO
    zip_bytes = io.BytesIO(resp.content)

    # Unpack
    with zipfile.ZipFile(zip_bytes) as z:
        z.extractall(TELEMETRY_DIR)

    print(f"Data unpacked into: {TELEMETRY_DIR}")


if __name__ == '__main__':
    fetch_and_unpack()
