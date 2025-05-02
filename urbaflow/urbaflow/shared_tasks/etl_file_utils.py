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


def split_csv_file(input_file: str, output_dir: str, lines_per_chunk: int) -> list[str]:
    """
    Split a large CSV file into multiple smaller chunks of specified line count.
    Returns a list of chunk file paths.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chunk_files = []
    current_chunk = 1
    current_chunk_path = os.path.join(output_dir, f"chunk_{current_chunk}.csv")
    out_f = open(current_chunk_path, "w", encoding="utf-8")
    chunk_files.append(current_chunk_path)

    with open(input_file, "r", encoding="utf-8") as in_f:
        header = next(in_f)
        out_f.write(header)

        line_count = 0
        for line in in_f:
            out_f.write(line)
            line_count += 1
            if line_count >= lines_per_chunk:
                out_f.close()
                current_chunk += 1
                current_chunk_path = os.path.join(
                    output_dir, f"chunk_{current_chunk}.csv"
                )
                out_f = open(current_chunk_path, "w", encoding="utf-8")
                out_f.write(header)
                chunk_files.append(current_chunk_path)
                line_count = 0
    out_f.close()
    return chunk_files
