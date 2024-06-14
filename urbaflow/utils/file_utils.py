import os
import pandas as pd
import pathlib
import logging
from chardet import detect


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


def list_files_at_path(path, ext="**/*"):
    files = [f for f in pathlib.Path(path).glob(ext) if f.is_file()]
    return files


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
    """
    print("encode_to_utf8: " + src_file)
    trg_file = src_file + ".swp"
    from_codec = get_encoding_type(src_file)
    if from_codec == "utf-8":
        logging.Logger.info("Already UTF-8")
        return
    try:
        with open(src_file, "r", encoding=from_codec) as f, open(
            trg_file, "w", encoding="utf-8"
        ) as e:
            text = f.read()
            e.write(text)
        os.remove(src_file)
        os.rename(trg_file, src_file)
    except UnicodeDecodeError:
        logging.Logger.error("Decode Error")
    except UnicodeEncodeError:
        logging.Logger.error("Encode Error")
