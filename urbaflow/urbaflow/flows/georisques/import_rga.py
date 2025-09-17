from shared_tasks.config import TEMP_DIR
from shared_tasks.etl_ogr_utils import import_shapefile
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger
from shared_tasks.etl_file_utils import download_and_unzip

logger = get_logger(__name__)


def import_rga_shape(
    files, schema="public", table: str = "risques_rga", replace: bool = False
):
    for file in files:
        logger.info("Importing file: %s", file)
        import_shapefile(
            file=file,
            table=table,
            source_srs="EPSG:2154",
            destination_srs="EPSG:2154",
            schema=schema,
            replace=replace,
        )


def import_rga_flow(
    dirname, department: str, schema: str = "public", replace: bool = False
):
    """
    Import data from Georisques RGA (Retrait Gonflement des Argiles).
    Si le répertoire n'est pas fourni, le département doit être spécifié pour télécharger les données.

    https://files.georisques.fr/argiles/AleaRG76_L93.zip
    """
    if dirname is None and department is None:
        raise ValueError("Le nom du répertoire ou le département doit être fourni.")
    if department:
        logger.info(f"Downloading RGA data for department {department}")
        url = f"https://files.georisques.fr/argiles/AleaRG{department}_L93.zip"
        target_dir = TEMP_DIR / "georisques/rga" / department
        target_dir.mkdir(parents=True, exist_ok=True)

        download_and_unzip(url, extract_to_path=target_dir)
        dirname = target_dir
    files = list_files_at_path(dirname, r"AleaRG.*", extension=".shp")
    import_rga_shape(files, schema, replace=replace)
