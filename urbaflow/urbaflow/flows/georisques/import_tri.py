from shared_tasks.config import TEMP_DIR
from shared_tasks.etl_file_utils import download_and_unzip
from shared_tasks.etl_ogr_utils import import_shapefile
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)


def import_tri_shape(
    files, schema: str = "public", table: str = "risques_tri", replace: bool = False
):
    """
    Importe et consolide les fichiers shapefile TRI dans PostGIS.
    """
    for i, file in enumerate(files):
        logger.info("Importation du fichier : %s", file)
        # Pour le premier fichier, on applique 'replace' (si demandé).
        # Pour les fichiers suivants, on force replace=False pour ajouter
        # (append) les données.
        import_shapefile(
            file=file,
            table=table,
            source_srs="EPSG:2154",
            destination_srs="EPSG:2154",
            schema=schema,
            replace=replace if i == 0 else False,
        )


def import_tri_flow(
    dirname=None,
    department: str = None,
    schema: str = "public",
    table: str = "risques_tri",
    replace: bool = False,
):
    """
    Importe les données des Territoires à Risques Important d'Inondation (TRI 2020).
    Si le répertoire n'est pas fourni, le département doit être spécifié
    pour télécharger les données.
    Consolide les tables des surfaces inondables (zone qui sera inondée en cas
    d’occurrence d’une inondation d’un certain type selon un certain scénario)
    dans une seule table PostGIS.

    Nommage des fichiers consolidés :
    N_[prefixTri]_INONDABLE_[Alea]_[Scenario]_[NomCoursEau]_S_ddd
    simplifié à n_tri_*_inondable_*_s_*

    Exemple d'URL : https://files.georisques.fr/di_2020/tri_2020_sig_di_85.zip
    """
    if dirname is None and department is None:
        raise ValueError("Le nom du répertoire ou le département doit être fourni.")

    if department:
        logger.info(
            "Téléchargement des données TRI 2020 pour le département %s", department
        )
        url = f"https://files.georisques.fr/di_2020/tri_2020_sig_di_{department}.zip"
        target_dir = TEMP_DIR / "georisques/tri" / department
        target_dir.mkdir(parents=True, exist_ok=True)

        download_and_unzip(url, extract_to_path=target_dir)
        dirname = target_dir

    files = list_files_at_path(
        dirname, r".*n_tri_.*_inondable_.*_s_.*", extension=".shp"
    )
    if not files:
        files = list_files_at_path(dirname, r".*inondable.*", extension=".shp")
    if not files:
        files = list_files_at_path(dirname, r".*", extension=".shp")

    import_tri_shape(files, schema=schema, table=table, replace=replace)
