import requests
import zipfile
import io
import os
import gzip


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


def unzip_file_in_place(archive_path):
    # get directory where archive_path is stored
    dir_path = os.path.dirname(archive_path)
    file_root, _ = os.path.splitext(archive_path)  # split into file.ext and .gz

    src_name = archive_path
    dest_name = os.path.join(dir_path, file_root)
    with gzip.open(src_name, "rb") as infile:
        with open(dest_name, "wb") as outfile:
            for line in infile:
                outfile.write(line)
