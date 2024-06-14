from utils.file_utils import concat_files, list_files_at_path


def import_basias(path):
    files = list_files_at_path(path, "*.csv")
    df = concat_files(files)
    df.to_csv(path + "/basias.csv", index=False)
