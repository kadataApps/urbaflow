import gzip
import os
import ast
import sys
import urllib.request

from urbaflow.urbaflow.shared_tasks.logging_config import logger
from utils.dbutils import import_geojson
from .get_communes_majic import get_imported_communes_from_file


def reporthook(blocknum, blocksize, totalsize):
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r%5.1f%% %*d / %d" % (percent, len(str(totalsize)), readsofar, totalsize)
        sys.stderr.write(s)
        if readsofar >= totalsize:  # near the end
            sys.stderr.write("\n")
    else:  # total size is unknown
        sys.stderr.write("read %d\n" % (readsofar,))


def download_cadastre(codeinsee: str, target_dir, millesime):
    param_millesime = "latest" if millesime is None else millesime
    logger.info(
        "Téléchargement du cadastre pour la commune %s, millesime %s",
        codeinsee,
        param_millesime,
    )
    url = (
        "https://cadastre.data.gouv.fr/data/etalab-cadastre/"
        + param_millesime
        + "/geojson/communes/"
    )
    # url = 'https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/'
    url += codeinsee[0:2] + "/" + codeinsee
    url += "/cadastre-" + codeinsee
    url += "-parcelles.json.gz"
    # https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/77/77111/cadastre-77111-parcelles.json.gz

    file_name = url.split("/")[-1]

    if not (os.path.exists(target_dir)):
        os.makedirs(target_dir)
    dest_filename = os.path.join(target_dir, file_name)
    urllib.request.urlretrieve(url, dest_filename, reporthook)
    unzip_cadastre(dest_filename)
    return dest_filename


def download_bati(codeinsee, target_dir):
    url = "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/"
    url += codeinsee[0:2] + "/" + codeinsee
    url += "/cadastre-" + codeinsee
    url += "-batiments.json.gz"
    # https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/77/77111/cadastre-77111-bati.json.gz

    file_name = url.split("/")[-1]

    if not (os.path.exists(target_dir)):
        os.makedirs(target_dir)
    dest_filename = os.path.join(target_dir, file_name)
    urllib.request.urlretrieve(url, dest_filename, reporthook)
    unzip_cadastre(dest_filename)
    return dest_filename


def download_cadastre_for_communes():
    temp_dir = os.path.join(os.getcwd(), "temp/downloads/")
    config = get_imported_communes_from_file()
    try:
        communes = ast.literal_eval(config["communes"])
    except:
        logger.error("Aucune commune dans le fichier communes.txt. Rien à télécharger")
        raise
    else:
        millesime = os.getenv("CADASTRE_MILLESIME")
        logger.debug(communes)
        for commune in communes:
            logger.info(commune)
            download_cadastre(commune, temp_dir, millesime)
            file = os.path.join(temp_dir, "cadastre-%s-parcelles.json" % commune)
            import_geojson(file, "cadastre_parcelles")


def download_bati_for_communes():
    temp_dir = os.path.join(os.getcwd(), "temp/downloads/")
    config = get_imported_communes_from_file()
    try:
        communes = ast.literal_eval(config["communes"])
    except:
        logger.error("Aucune commune dans le fichier communes.txt. Rien à télécharger")
        raise
    else:
        logger.info(communes)
        for commune in communes:
            logger.info(commune)
            download_bati(commune, temp_dir)
            file = os.path.join(temp_dir, "cadastre-%s-batiments.json" % commune)
            import_geojson(file, "cadastre_bati")


def unzip_cadastre(archive_path):
    # get directory where archive_path is stored
    dir = os.path.dirname(archive_path)
    # filename = os.path.basename(archive_path)  # get filename
    file_json, file_json_ext = os.path.splitext(
        archive_path
    )  # split into file.json and .gz

    src_name = archive_path
    dest_name = os.path.join(dir, file_json)
    with gzip.open(src_name, "rb") as infile:
        with open(dest_name, "wb") as outfile:
            for line in infile:
                outfile.write(line)
