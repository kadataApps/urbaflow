from pathlib import Path

import geopandas as gpd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import (
    create_table_from_geodataframe,
    load,
)
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger

# Base des immeubles protégés au titre des Monuments Historiques (MH)
# URL de téléchargement data.gouv.fr : https://www.data.gouv.fr/api/1/datasets/r/74376ed3-2ebd-4c5f-bf16-d5d05d151ad7

logger = get_logger(__name__)

MH_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/74376ed3-2ebd-4c5f-bf16-d5d05d151ad7"
)


@task
def fetch_mh_geodataframe(dirname: Path | None = None) -> gpd.GeoDataFrame:
    """
    Télécharge ou lit le fichier GeoJSON des Monuments Historiques
    et retourne un GeoDataFrame avec géométrie 'geom' reprojetée en EPSG:2154.
    """
    if dirname is None:
        logger.info("Téléchargement du fichier GeoJSON des MH depuis %s", MH_URL)
        headers = {"User-Agent": "Mozilla/5.0"}
        target_dir = TEMP_DIR / "mh"
        target_dir.mkdir(parents=True, exist_ok=True)
        geojson_path = target_dir / "monuments_historiques.geojson"

        response = requests.get(MH_URL, headers=headers, stream=True)
        response.raise_for_status()
        with open(geojson_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                f.write(chunk)
    else:
        logger.info("Recherche du fichier GeoJSON des MH dans %s", dirname)
        files = list_files_at_path(dirname, r".*", extension=".geojson")
        if not files:
            files = list_files_at_path(dirname, r".*", extension=".json")
        if not files:
            raise ValueError(f"Aucun fichier GeoJSON / JSON trouvé dans {dirname}")
        geojson_path = Path(files[0])

    logger.info("Lecture du GeoJSON MH depuis %s", geojson_path)
    gdf = gpd.read_file(str(geojson_path))

    logger.info("Reprojection du GeoDataFrame MH en Lambert 93 (EPSG:2154)")
    gdf = gdf.rename_geometry("geom")
    gdf = gdf.to_crs("EPSG:2154")

    return gdf


@task
def load_mh_geodataframe(
    gdf: gpd.GeoDataFrame,
    db_schema: str = "public",
    table_name: str = "patrimoine_immeubles_proteges_mh",
    recreate: bool = True,
):
    """
    Crée la table PostGIS et charge le GeoDataFrame des Monuments Historiques.
    """
    e = create_engine()
    with e.begin() as conn:
        logger.info(
            "Création de la table %s.%s (recreate=%s)", db_schema, table_name, recreate
        )
        create_table_from_geodataframe(
            gdf=gdf,
            connection=conn,
            table_name=table_name,
            schema=db_schema,
            recreate=recreate,
            srs=2154,
            logger=logger,
        )
        logger.info(
            "Insertion de %d enregistrements dans %s.%s",
            len(gdf),
            db_schema,
            table_name,
        )
        load(
            gdf,
            connection=conn,
            table_name=table_name,
            schema=db_schema,
            how="append",
            logger=logger,
        )


@flow
def import_mh_flow(
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "patrimoine_immeubles_proteges_mh",
    recreate: bool = True,
):
    """
    Flow d'importation des immeubles protégés au titre des Monuments Historiques (MH).
    Si le répertoire n'est pas fourni, le GeoJSON est téléchargé.
    """
    logger.info("Début de l'import des Monuments Historiques (MH)")
    gdf = fetch_mh_geodataframe(dirname=dirname)
    load_mh_geodataframe(
        gdf=gdf,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )
    logger.info("Import des Monuments Historiques terminé avec succès !")
