from pathlib import Path

import duckdb
import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import load
from shared_tasks.file_utils import list_files_at_path
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

# Base Sirene géolocalisée (GeoSirene - GeoParquet)
# URL stable data.gouv.fr : https://www.data.gouv.fr/api/1/datasets/r/672007af-0146-491f-835c-8314d63fa44e

logger = get_logger(__name__)

GEOSIRENE_PARQUET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/672007af-0146-491f-835c-8314d63fa44e"
)


@task
def fetch_geosirene_parquet(dirname: Path | None = None) -> Path:
    """
    Télécharge le fichier GeoParquet GeoSirene s'il n'est pas fourni localement.
    """
    if dirname is None:
        target_dir = TEMP_DIR / "geosirene"
        target_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = target_dir / "geosirene.parquet"

        if not parquet_path.exists():
            logger.info(
                "Téléchargement du fichier GeoParquet GeoSirene depuis %s",
                GEOSIRENE_PARQUET_URL,
            )
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(
                GEOSIRENE_PARQUET_URL, headers=headers, stream=True
            )
            response.raise_for_status()
            with open(parquet_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    f.write(chunk)
            logger.info(
                "Téléchargement du fichier GeoParquet terminé : %s", parquet_path
            )
        else:
            logger.info(
                "Fichier GeoParquet GeoSirene trouvé en cache local : %s",
                parquet_path,
            )
        return parquet_path
    else:
        logger.info("Recherche du fichier parquet GeoSirene dans %s", dirname)
        files = list_files_at_path(dirname, r".*", extension=".parquet")
        if not files:
            raise ValueError(f"Aucun fichier .parquet trouvé dans {dirname}")
        return Path(files[0])


@task
def create_geosirene_etablissement_table(
    db_schema: str = "public",
    table_name: str = "geosirene_etablissement",
    recreate: bool = True,
):
    """
    Crée la table geosirene_etablissement dans PostGIS.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {q(db_schema)}.{q(table_name)}"))
            logger.info(
                "Suppression de la table %s.%s si elle existe", db_schema, table_name
            )

        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {q(db_schema)}.{q(table_name)} (
                    siret text PRIMARY KEY,
                    x double precision,
                    y double precision,
                    qualite_xy text,
                    epsg text,
                    plg_qp24 text,
                    plg_iris text,
                    plg_zus text,
                    plg_qp15 text,
                    plg_qva text,
                    plg_code_commune text,
                    distance_precision double precision,
                    qualite_qp24 text,
                    qualite_iris text,
                    qualite_zus text,
                    qualite_qp15 text,
                    qualite_qva text,
                    y_latitude double precision,
                    x_longitude double precision,
                    urbaflow_departement text,
                    urbaflow_inserted_at timestamp
                )
                """
            )
        )
        logger.info(
            "Table %s.%s créée si elle n'existait pas auparavant",
            db_schema,
            table_name,
        )


@task
def extract_and_load_geosirene(
    parquet_path: Path,
    department: str | None = None,
    db_schema: str = "public",
    table_name: str = "geosirene_etablissement",
    recreate: bool = False,
):
    """
    Extrait les enregistrements GeoSirene (filtrés par département si spécifié)
    et les insère dans la table PostGIS.
    """
    con = duckdb.connect()
    where_clause = ""
    dep_str = None

    if department:
        dep_str = str(department).strip()
        where_clause = f"WHERE plg_code_commune LIKE '{dep_str}%'"
        logger.info(
            "Extraction des établissements GeoSirene pour le département %s", dep_str
        )
    else:
        logger.info("Extraction de la totalité des établissements GeoSirene")

    query = f"""
        SELECT 
            siret, x, y, qualite_xy, epsg, plg_qp24, plg_iris, plg_zus,
            plg_qp15, plg_qva, plg_code_commune, distance_precision,
            qualite_qp24, qualite_iris, qualite_zus, qualite_qp15,
            qualite_qva, y_latitude, x_longitude
        FROM '{parquet_path.as_posix()}'
        {where_clause}
    """

    df = con.execute(query).df()
    if df.empty:
        logger.warning(
            "Aucun établissement GeoSirene trouvé avec la requête : %s", query
        )
        return

    df["siret"] = df["siret"].astype(str)
    df = df.drop_duplicates(subset=["siret"])
    df["urbaflow_departement"] = dep_str
    df["urbaflow_inserted_at"] = pd.Timestamp.now()

    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if not recreate and dep_str:
            logger.info(
                "Suppression des anciens établissements du département %s dans %s.%s",
                dep_str,
                db_schema,
                table_name,
            )
            conn.execute(
                text(
                    f"DELETE FROM {q(db_schema)}.{q(table_name)} "
                    "WHERE plg_code_commune LIKE :dep_pattern "
                    "OR urbaflow_departement = :dep"
                ),
                {"dep_pattern": f"{dep_str}%", "dep": dep_str},
            )

        logger.info(
            "Insertion de %d établissements dans %s.%s", len(df), db_schema, table_name
        )
        load(
            df,
            connection=conn,
            table_name=table_name,
            schema=db_schema,
            how="append",
            logger=logger,
        )


@task
def add_geometry_column_to_table(
    db_schema: str = "public", table_name: str = "geosirene_etablissement"
):
    """
    Ajoute la colonne de géométrie geom (Lambert 93 / EPSG:2154) et l'index GIST.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                ALTER TABLE {q(db_schema)}.{q(table_name)} 
                    ADD COLUMN IF NOT EXISTS 
                    geom geometry(POINT, 2154);
                CREATE INDEX IF NOT EXISTS {q(f"sidx_{table_name}_geom")}
                    ON {q(db_schema)}.{q(table_name)} USING GIST (geom);
                """
            )
        )


@task
def populate_geom(
    db_schema: str = "public", table_name: str = "geosirene_etablissement"
):
    """
    Calcul des géométries Lambert 93 à partir des coordonnées (x_longitude, y_latitude).
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        logger.info("Mise à jour des géométries geom dans %s.%s", db_schema, table_name)
        conn.execute(
            text(
                f"""
                UPDATE {q(db_schema)}.{q(table_name)}
                SET geom = ST_Transform(
                    ST_SetSRID(ST_MakePoint(x_longitude, y_latitude), 4326),
                    2154
                )
                WHERE x_longitude IS NOT NULL AND y_latitude IS NOT NULL;
                """
            )
        )


@flow
def import_geosirene_data(
    department: str | None = None,
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "geosirene_etablissement",
    recreate: bool = True,
):
    """
    Flow d'importation des établissements géolocalisés GeoSirene (format GeoParquet).
    """
    logger.info("Début de l'import GeoSirene")
    parquet_path = fetch_geosirene_parquet(dirname=dirname)
    create_geosirene_etablissement_table(
        db_schema=db_schema, table_name=table_name, recreate=recreate
    )
    add_geometry_column_to_table(db_schema=db_schema, table_name=table_name)
    extract_and_load_geosirene(
        parquet_path=parquet_path,
        department=department,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )
    populate_geom(db_schema=db_schema, table_name=table_name)
    logger.info("Import GeoSirene terminé avec succès !")
