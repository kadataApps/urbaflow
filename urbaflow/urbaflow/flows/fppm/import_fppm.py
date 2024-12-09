import pathlib
import pandas as pd


def concat_files(files):
    frames = [
        pd.read_csv(f, sep=";", encoding="latin-1", low_memory=False) for f in files
    ]
    return pd.concat(frames, ignore_index=True)


def list_files_at_path(path, ext="**/*"):
    files = [f for f in pathlib.Path(path).glob(ext) if f.is_file()]
    return files


def import_fppm(path):
    files = list_files_at_path(path, "*.txt")
    df = concat_files(files)
    df.to_csv(path + "/fppm.csv", index=False)
