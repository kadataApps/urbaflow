import requests
import zipfile
import io
import os


def download_and_unzip(url, extract_to_path="."):
    """
    Download a zip file from a URL and unzip it to a specified directory.

    Parameters:
    url (str): The URL of the zip file to download.
    extract_to_path (str): The directory to extract the contents to. Defaults to the current directory.
    """
    response = requests.get(url)

    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(extract_to_path)
        print(f"Successfully extracted to {os.path.abspath(extract_to_path)}")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")
