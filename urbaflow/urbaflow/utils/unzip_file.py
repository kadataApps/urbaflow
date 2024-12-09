import os
import gzip


def unzip_file_in_place(archive_path):
    # get directory where archive_path is stored
    dir_path = os.path.dirname(archive_path)
    file_root, _ = os.path.splitext(archive_path)  # split into file.json and .gz

    src_name = archive_path
    dest_name = os.path.join(dir_path, file_root)
    with gzip.open(src_name, "rb") as infile:
        with open(dest_name, "wb") as outfile:
            for line in infile:
                outfile.write(line)
