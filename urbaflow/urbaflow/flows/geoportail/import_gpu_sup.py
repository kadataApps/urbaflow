import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.etl_ogr_utils import import_shapefile
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger

# Données SUP du Géoportail de l'Urbanisme (GPU)
# Flux XML d'extraction : https://www.geoportail-urbanisme.gouv.fr/api/extraction/download-latest

logger = get_logger(__name__)

DOWNLOAD_LATEST_URL = (
    "https://www.geoportail-urbanisme.gouv.fr/api/extraction/download-latest"
)

SUP_TABLE_NAMES = {
    "acte_sup",
    "assiette_sup_l",
    "assiette_sup_p",
    "assiette_sup_s",
    "generateur_sup_l",
    "generateur_sup_p",
    "generateur_sup_s",
    "gestionnaire_sup",
    "servitude",
    "servitude_acte_sup",
}


def extract_table_name_from_filename(filename: str) -> str | None:
    """
    Extrait le nom de la table SUP à partir du nom de fichier GeoPackage.
    Exemple : schema_xxx.assiette_sup_l.gpkg -> assiette_sup_l
    """
    parts = filename.split(".")
    if len(parts) >= 2 and parts[-1] == "gpkg":
        candidate = parts[-2]
        if (
            candidate in SUP_TABLE_NAMES
            or "sup" in candidate
            or "servitude" in candidate
        ):
            return candidate
    return None


@task
def fetch_sup_gpkg_urls() -> dict[str, str]:
    """
    Interroge l'API download-latest du Géoportail de l'Urbanisme
    et retourne les URL des fichiers GeoPackage correspondant aux SUP.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(DOWNLOAD_LATEST_URL, headers=headers)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    sup_urls = {}
    for entry in root.findall("atom:entry", ns):
        link = entry.find("atom:link", ns)
        if link is not None:
            href = link.attrib.get("href")
            if href and href.endswith(".gpkg"):
                filename = href.split("/")[-1]
                table_name = extract_table_name_from_filename(filename)
                if table_name:
                    sup_urls[table_name] = href

    logger.info("Trouvé %d table(s) SUP dans le flux Géoportail", len(sup_urls))
    return sup_urls


@task
def download_gpkg_file(url: str, dest_path: Path) -> None:
    """
    Télécharge un fichier GeoPackage depuis une URL vers le chemin destination.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    logger.info("Téléchargement du fichier depuis %s", url)
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


@task
def import_gpu_sup_files(
    files_mapping: dict[str, Path],
    schema: str = "public",
    replace: bool = True,
) -> None:
    """
    Importe les fichiers GeoPackage SUP dans PostGIS préfixés par gp_.
    """
    for table_name, file_path in files_mapping.items():
        target_table = (
            table_name if table_name.startswith("gp_") else f"gp_{table_name}"
        )
        logger.info(
            "Importation de la table SUP %s vers %s.%s depuis %s",
            table_name,
            schema,
            target_table,
            file_path,
        )
        import_shapefile(
            file=str(file_path),
            table=target_table,
            source_srs="EPSG:4326",
            destination_srs="EPSG:2154",
            schema=schema,
            replace=replace,
        )


@flow
def import_gpu_sup_flow(
    dirname: Path | None = None,
    schema: str = "public",
    replace: bool = True,
) -> None:
    """
    Flow d'importation des données SUP du Géoportail de l'Urbanisme (GPU).
    Télécharge et intègre l'ensemble des fichiers GeoPackage SUP en les préfixant
    par gp_ dans PostGIS (ex: gp_acte_sup, gp_assiette_sup_s, gp_servitude, etc.).
    """
    if dirname is None:
        logger.info(
            "Récupération de la liste des fichiers SUP via l'API Géoportail"
        )
        sup_urls = fetch_sup_gpkg_urls()
        target_dir = TEMP_DIR / "geoportail/sup"
        target_dir.mkdir(parents=True, exist_ok=True)

        files_mapping = {}
        for table_name, url in sup_urls.items():
            file_path = target_dir / f"{table_name}.gpkg"
            download_gpkg_file(url, file_path)
            files_mapping[table_name] = file_path
    else:
        logger.info(
            "Importation des fichiers GPKG SUP depuis le dossier local %s", dirname
        )
        gpkg_files = list_files_at_path(dirname, r".*", extension=".gpkg")
        files_mapping = {}
        for gpkg_file in gpkg_files:
            file_path = Path(gpkg_file)
            table_name = extract_table_name_from_filename(file_path.name)
            if table_name:
                files_mapping[table_name] = file_path

    import_gpu_sup_files(files_mapping, schema=schema, replace=replace)
