from shared_tasks.config import TEMP_DIR
from shared_tasks.etl_file_utils import download_and_unzip
from shared_tasks.etl_ogr_utils import import_shapefile
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)


def import_remnappes_shape(
    files,
    schema: str = "public",
    table: str = "risques_remnappes",
    replace: bool = False,
):
    """
    Importe les fichiers shapefile de remontée de nappe dans PostGIS.
    """
    for file in files:
        logger.info("Importation du fichier : %s", file)
        import_shapefile(
            file=file,
            table=table,
            source_srs="EPSG:2154",
            destination_srs="EPSG:2154",
            schema=schema,
            replace=replace,
        )


def import_remnappes_flow(
    dirname=None,
    department: str = None,
    schema: str = "public",
    table: str = "risques_remnappes",
    replace: bool = False,
):
    """
    Importe les données Géorisques REMNAPPES (Risque inondation par remontée de nappe).
    Si le répertoire n'est pas fourni, le département doit être spécifié
    pour télécharger les données.

    Exemple d'URL : https://files.georisques.fr/REMNAPPES/Dept_85.zip
    """
    if dirname is None and department is None:
        raise ValueError("Le nom du répertoire ou le département doit être fourni.")

    if department:
        logger.info(
            "Téléchargement des données REMNAPPES pour le département %s", department
        )
        url = f"https://files.georisques.fr/REMNAPPES/Dept_{department}.zip"
        target_dir = TEMP_DIR / "georisques/remnappes" / department
        target_dir.mkdir(parents=True, exist_ok=True)

        download_and_unzip(url, extract_to_path=target_dir)
        dirname = target_dir

    files = list_files_at_path(dirname, r".*Nappe.*|.*nappe.*", extension=".shp")
    if not files:
        files = list_files_at_path(dirname, r".*", extension=".shp")

    import_remnappes_shape(files, schema=schema, table=table, replace=replace)
