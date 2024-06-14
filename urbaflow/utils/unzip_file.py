import os
import gzip


def unzip_file_in_place(archivePath):
    # get directory where archivePath is stored
    dir = os.path.dirname(archivePath)
    # filename = os.path.basename(archivePath)  # get filename
    file_root, file_archive_ext = os.path.splitext(
        archivePath
    )  # split into file.json and .gz

    src_name = archivePath
    dest_name = os.path.join(dir, file_root)
    with gzip.open(src_name, "rb") as infile:
        with open(dest_name, "wb") as outfile:
            for line in infile:
                outfile.write(line)
