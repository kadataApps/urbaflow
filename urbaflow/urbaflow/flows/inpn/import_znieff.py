from prefect import flow, task
from shared_tasks.etl_file_utils import download_and_unzip
from shared_tasks.etl_ogr_utils import import_shapefile
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger


# ZNIEFF continentales de métropole
url_znieff1 = "https://inpn.mnhn.fr/docs/Shape/znieff1.zip"
url_znieff2 = "https://inpn.mnhn.fr/docs/Shape/znieff2.zip"


@task
def download_znieff(url, path, znieff_type):
    download_and_unzip(url, extract_to_path=path)
    if znieff_type == "1":
        files = list_files_at_path(path, r"znieff1.*", extension=".shp")
    elif znieff_type == "2":
        files = list_files_at_path(path, r"znieff2.*", extension=".shp")

    if len(files) == 0:
        raise ValueError("No file found")
    return files[0]


@task
def import_znieff_shape(file, schema="public", table=None):
    if table is None:
        raise ValueError("Table name must be provided")
    logger = get_logger()
    logger.info(f"Importing file: {file}")
    import_shapefile(
        file=file,
        table=table,
        source_srs="EPSG:2154",
        destination_srs="EPSG:2154",
        schema=schema,
    )


@flow
def import_znieff_flow(path, schema="public"):
    logger = get_logger()
    logger.info(f"Downloading ZNIEFF 1. Url: {url_znieff1}")
    file = download_znieff(url_znieff1, path, "1")
    import_znieff_shape(file, schema, "inpn_znieff1")

    logger.info(f"Downloading ZNIEFF 2. Url: {url_znieff2}")
    file = download_znieff(url_znieff2, path, "2")
    import_znieff_shape(file, schema, "inpn_znieff2")
