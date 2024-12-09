import os
import re

from utils.dbutils import import_shapefile


def list_shp_files_at_path(path, regex):
    shp_files = []
    pattern = re.compile(regex)

    for root, dirs, files in os.walk(path):
        for file in files:
            if pattern.match(file) and file.endswith(".shp"):
                file_path = os.path.join(root, file)
                shp_files.append(file_path)

    return shp_files


def import_tri(files, schema):
    for file in files:
        print("Importing file: ", file)
        table = os.path.basename(file).split(".")[0]
        import_shapefile(file, table, schema)


def import_tri_files(path):
    files = list_shp_files_at_path(path, r"n_inondable_.*")
    import_tri(files, "clairsienne")
