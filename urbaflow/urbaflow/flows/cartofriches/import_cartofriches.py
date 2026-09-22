# https://www.data.gouv.fr/fr/datasets/sites-references-dans-cartofriches/

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
from sqlalchemy import DDL

# Sites référencés dans Cartofriches (friches industrielles, commerciales, etc.)
# URL de téléchargement data.gouv.fr :
# https://www.data.gouv.fr/api/1/datasets/r/a9084493-e742-4a2f-890b-0ebc803098df

logger = get_logger(__name__)

CARTOFRICHES_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/a9084493-e742-4a2f-890b-0ebc803098df"
)

CARTOFRICHES_LAYER_NAME = "friches_surfaces"


@task
def fetch_cartofriches_geodataframe(dirname: Path | None = None) -> gpd.GeoDataFrame:
    """
    Télécharge ou lit le fichier GeoPackage des sites référencés dans Cartofriches
    et retourne un GeoDataFrame avec géométrie 'geom' reprojetée en EPSG:2154.
    """
    if dirname is None:
        logger.info(
            "Téléchargement du fichier GeoPackage Cartofriches depuis %s",
            CARTOFRICHES_URL,
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        target_dir = TEMP_DIR / "cartofriches"
        target_dir.mkdir(parents=True, exist_ok=True)
        gpkg_path = target_dir / "cartofriches.gpkg"

        response = requests.get(CARTOFRICHES_URL, headers=headers, stream=True)
        response.raise_for_status()
        with open(gpkg_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                f.write(chunk)
    else:
        logger.info("Recherche du fichier GeoPackage Cartofriches dans %s", dirname)
        files = list_files_at_path(dirname, r".*", extension=".gpkg")
        if not files:
            raise ValueError(f"Aucun fichier GeoPackage (.gpkg) trouvé dans {dirname}")
        gpkg_path = Path(files[0])

    logger.info("Lecture du GeoPackage Cartofriches depuis %s", gpkg_path)
    gdf = gpd.read_file(str(gpkg_path), layer=CARTOFRICHES_LAYER_NAME)

    logger.info("Normalisation des noms de colonnes en minuscules")
    gdf.columns = [str(column).lower() for column in gdf.columns]

    logger.info("Reprojection du GeoDataFrame Cartofriches en Lambert 93 (EPSG:2154)")
    gdf = gdf.rename_geometry("geom")
    gdf = gdf.to_crs("EPSG:2154")

    return gdf


@task
def load_cartofriches_geodataframe(
    gdf: gpd.GeoDataFrame,
    db_schema: str = "public",
    table_name: str = "friches_cartofriches",
    recreate: bool = True,
):
    """
    Crée la table PostGIS et charge le GeoDataFrame des sites Cartofriches.
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
        q = conn.engine.dialect.identifier_preparer.quote
        logger.info("Création de l'index spatial sur %s.%s", db_schema, table_name)
        conn.execute(
            DDL(
                f"""
                CREATE INDEX IF NOT EXISTS {q(f"sidx_{table_name}_geom")}
                ON {q(db_schema)}.{q(table_name)} USING GIST (geom)
                """
            )
        )


@flow
def import_cartofriches_flow(
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "friches_cartofriches",
    recreate: bool = True,
) -> None:
    """
    Flow d'importation des sites référencés dans Cartofriches.
    Si le répertoire n'est pas fourni, le GeoPackage national est téléchargé
    depuis data.gouv.fr.
    """
    logger.info("Début de l'import des sites Cartofriches")
    gdf = fetch_cartofriches_geodataframe(dirname=dirname)
    load_cartofriches_geodataframe(
        gdf=gdf,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )
    logger.info("Import des sites Cartofriches terminé avec succès !")
