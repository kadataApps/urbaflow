from pathlib import Path

import geopandas as gpd
import pandas as pd
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

# Liste des édifices labellisés Architecture Contemporaine Remarquable (ACR)
# Description : https://www.data.gouv.fr/datasets/liste-des-edifices-labellises-architecture-contemporaine-remarquable-acr
# URL de téléchargement data.gouv.fr : https://www.data.gouv.fr/api/1/datasets/r/80b6ac20-41b1-400c-8860-af201ff7dcb6

logger = get_logger(__name__)

ACR_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/80b6ac20-41b1-400c-8860-af201ff7dcb6"
)
ACR_CSV_SEPARATOR = "|"
ACR_COORDINATES_COLUMN = "coordonnees"


def download_acr_csv(target_dir: Path) -> Path:
    """
    Télécharge le fichier CSV national des édifices ACR dans le répertoire cible
    et retourne son chemin.
    """
    logger.info("Téléchargement du fichier CSV des ACR depuis %s", ACR_URL)
    target_dir.mkdir(parents=True, exist_ok=True)
    csv_path = target_dir / "architecture_contemporaine_remarquable.csv"

    response = requests.get(ACR_URL, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
    response.raise_for_status()
    with open(csv_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=65536):
            f.write(chunk)
    return csv_path


def find_acr_csv(dirname: Path) -> Path:
    """
    Recherche le fichier CSV des ACR dans le répertoire fourni.
    """
    logger.info("Recherche du fichier CSV des ACR dans %s", dirname)
    files = list_files_at_path(dirname, r".*", extension=".csv")
    if not files:
        raise ValueError(f"Aucun fichier CSV trouvé dans {dirname}")
    return Path(files[0])


def build_acr_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Construit un GeoDataFrame à partir du DataFrame ACR.

    La colonne 'coordonnees' contient des coordonnées WGS84 au format 'lat,lon'.
    Les édifices sans coordonnées sont conservés avec une géométrie nulle.
    Le GeoDataFrame retourné a une géométrie 'geom' en Lambert 93 (EPSG:2154).
    """
    coordinates = df[ACR_COORDINATES_COLUMN].fillna("").str.split(",", expand=True)
    latitude = pd.to_numeric(coordinates[0], errors="coerce")
    longitude = pd.to_numeric(coordinates.get(1), errors="coerce")

    missing_mask = latitude.isna() | longitude.isna()
    if missing_mask.any():
        logger.warning(
            "%d édifices ACR sans coordonnées valides (géométrie nulle)",
            int(missing_mask.sum()),
        )

    points = gpd.GeoSeries(
        gpd.points_from_xy(longitude, latitude), index=df.index, crs="EPSG:4326"
    ).where(~missing_mask, None)
    gdf = gpd.GeoDataFrame(df, geometry=points, crs="EPSG:4326")
    logger.info("Reprojection du GeoDataFrame ACR en Lambert 93 (EPSG:2154)")
    return gdf.rename_geometry("geom").to_crs("EPSG:2154")


@task
def fetch_acr_geodataframe(dirname: Path | None = None) -> gpd.GeoDataFrame:
    """
    Télécharge ou lit le fichier CSV des édifices labellisés
    Architecture Contemporaine Remarquable (ACR) et retourne un GeoDataFrame
    avec géométrie 'geom' reprojetée en EPSG:2154.
    """
    csv_path = (
        download_acr_csv(TEMP_DIR / "acr") if dirname is None else find_acr_csv(dirname)
    )

    logger.info("Lecture du CSV ACR depuis %s", csv_path)
    df = pd.read_csv(
        csv_path,
        sep=ACR_CSV_SEPARATOR,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
    )
    df.columns = [column.lower() for column in df.columns]
    logger.info("%d édifices ACR lus", len(df))

    return build_acr_geodataframe(df)


@task
def load_acr_geodataframe(
    gdf: gpd.GeoDataFrame,
    db_schema: str = "public",
    table_name: str = "patrimoine_architecture_contemporaine_remarquable",
    recreate: bool = True,
):
    """
    Crée la table PostGIS et charge le GeoDataFrame des édifices ACR.
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
def import_acr_flow(
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "patrimoine_architecture_contemporaine_remarquable",
    recreate: bool = True,
):
    """
    Flow d'importation des édifices labellisés Architecture Contemporaine
    Remarquable (ACR). Si le répertoire n'est pas fourni, le CSV est téléchargé.
    """
    logger.info("Début de l'import des édifices Architecture Contemporaine Remarquable")
    gdf = fetch_acr_geodataframe(dirname=dirname)
    load_acr_geodataframe(
        gdf=gdf,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )
    logger.info("Import des édifices ACR terminé avec succès !")
