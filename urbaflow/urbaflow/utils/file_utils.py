import os
import re
import pandas as pd
from chardet import detect
from prefect import get_run_logger


def concat_files(files, sep=";"):
    frames = [
        pd.read_csv(f, sep=sep, encoding=get_encoding_type(f), low_memory=False)
        for f in files
    ]
    return pd.concat(frames, ignore_index=True)


def concat_files_with_encoding(files, encoding="latin-1"):
    frames = [
        pd.read_csv(f, sep=";", encoding=encoding, low_memory=False) for f in files
    ]
    return pd.concat(frames, ignore_index=True)


def list_files_at_path(path, regex, extension=".csv"):
    matching_files = []
    pattern = re.compile(regex)
    for root, dirs, files in os.walk(path):
        for file in files:
            if pattern.match(file) and file.endswith(extension):
                file_path = os.path.join(root, file)
                matching_files.append(file_path)
    return matching_files


def get_encoding_type(file):
    """
    get file encoding type for file
    """
    with open(file, "rb") as f:
        raw_data = f.read()
    return detect(raw_data)["encoding"]


def encode_to_utf8(src_file):
    """
    encode file to utf-8
    
    Replaces the file with a new file with the same name but encoded in utf-8
    """
    logger = get_run_logger()
    logger.info("encode_to_utf8: " + src_file)
    trg_file = src_file + ".swp"
    from_codec = get_encoding_type(src_file)
    if from_codec == "utf-8":
        logger.info("Already UTF-8")
        return
    try:
        logger.info(f"Converting {src_file} from {from_codec} to utf-8")
        with open(src_file, "r", encoding=from_codec) as f, open(
            trg_file, "w", encoding="utf-8"
        ) as e:
            text = f.read()
            e.write(text)
        os.remove(src_file)
        os.rename(trg_file, src_file)
    except UnicodeDecodeError:
        logger.error("Decode Error")
    except UnicodeEncodeError:
        logger.error("Encode Error")
