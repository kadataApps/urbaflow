from shared_tasks.config import TEMP_DIR
from shared_tasks.etl_file_utils import download_and_unzip
from shared_tasks.etl_ogr_utils import import_shapefile
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)


def import_icpe_shape(
    files,
    schema: str = "public",
    table: str = "risques_icpe",
    replace: bool = False,
):
    """
    Importe les fichiers shapefile ICPE (WGS84 -> Lambert 93) dans PostGIS.
    """
    for file in files:
        logger.info("Importation du fichier ICPE : %s", file)
        import_shapefile(
            file=file,
            table=table,
            source_srs="EPSG:4326",
            destination_srs="EPSG:2154",
            schema=schema,
            replace=replace,
        )


def import_icpe_flow(
    dirname=None,
    schema: str = "public",
    table: str = "risques_icpe",
    replace: bool = False,
):
    """
    Importe les données des Installations Classées (ICPE).
    La base est nationale (format shapefile, projection WGS84).
    Si le répertoire n'est pas fourni, le fichier ZIP national est téléchargé.

    URL WFS : https://mapsref.brgm.fr/wxs/georisques/georisques_dl?&service=wfs&version=2.0.0&request=getfeature&typename=InstallationsClassees&outputformat=SHAPEZIP
    """
    if dirname is None:
        logger.info("Téléchargement de la base nationale des ICPE")
        url = (
            "https://mapsref.brgm.fr/wxs/georisques/georisques_dl?"
            "&service=wfs&version=2.0.0&request=getfeature"
            "&typename=InstallationsClassees&outputformat=SHAPEZIP"
        )
        target_dir = TEMP_DIR / "georisques/icpe"
        target_dir.mkdir(parents=True, exist_ok=True)

        download_and_unzip(url, extract_to_path=target_dir)
        dirname = target_dir

    files = list_files_at_path(
        dirname, r".*InstallationsClassees.*|.*icpe.*", extension=".shp"
    )
    if not files:
        files = list_files_at_path(dirname, r".*", extension=".shp")

    import_icpe_shape(files, schema=schema, table=table, replace=replace)
