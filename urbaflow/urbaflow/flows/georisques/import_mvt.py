import os
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import load
from shared_tasks.file_utils import encode_to_utf8, list_files_at_path
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL

# Les données de mouvements de terrain sont disponibles sur le site Georisques
# Exemple : https://www.georisques.gouv.fr/webappReport/ws/mvmt/departements/85/fichecommunes.csv

logger = get_logger(__name__)


@task
def create_table_mvt(
    schema: str = "public", table_name: str = "risques_mvt", recreate: bool = True
):
    """
    Create the table in the database
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {q(schema)}.{q(table_name)}"))
            logger.info(f"Dropping table {schema}.{table_name} if it exists")

        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {q(schema)}.{q(table_name)} (
                    idmvt text PRIMARY KEY,
                    conf text,
                    x_saisi numeric,
                    y_saisi numeric,
                    epsg integer,
                    num_insee text,
                    commune text,
                    date_debut text,
                    lieu_dit text,
                    type_mvt text,
                    libelle_type text,
                    fiabilite_type text,
                    libelle_fiabilite text,
                    prec_date text,
                    libelle_date text,
                    prec_xy integer,
                    libelle_prec text,
                    longitude numeric,
                    latitude numeric
                )
                """
            )
        )


@task
def load_mvt(file: str, schema: str = "public", table_name: str = "risques_mvt"):
    """
    Import des données de mouvements de terrain à partir d'un fichier CSV.
    Les données sont importées dans la table du schéma spécifié.
    """
    logger.info("Importing file: " + file)

    mvt_df = pd.read_csv(file, sep=";", encoding="UTF-8", low_memory=False)
    ## renommage des colonnes pour correspondre au schéma de la table
    ## (snake_case, clarification des noms)
    mvt_df = mvt_df.rename(
        columns={
            "idMvt": "idmvt",
            "xsaisi": "x_saisi",
            "ysaisi": "y_saisi",
            "dateDebut": "date_debut",
            "typeMvt": "type_mvt",
            "libelleType": "libelle_type",
            "fiabiliteType": "fiabilite_type",
            "libelleFiabilite": "libelle_fiabilite",
            "PrecDate": "prec_date",
            "libelleDate": "libelle_date",
            "libellePrec": "libelle_prec",
            "longitudeDoublePrec": "longitude",
            "latitudeDoublePrec": "latitude",
        }
    )

    mvt_df["idmvt"] = mvt_df["idmvt"].astype(str)
    mvt_df = mvt_df.drop_duplicates(subset=["idmvt"])

    # extraction des colonnes à importer
    mvt_df = mvt_df[
        [
            "idmvt",
            "conf",
            "x_saisi",
            "y_saisi",
            "epsg",
            "num_insee",
            "commune",
            "date_debut",
            "lieu_dit",
            "type_mvt",
            "libelle_type",
            "fiabilite_type",
            "libelle_fiabilite",
            "prec_date",
            "libelle_date",
            "prec_xy",
            "libelle_prec",
            "longitude",
            "latitude",
        ]
    ]

    e = create_engine()
    with e.begin() as conn:
        load(
            mvt_df,
            connection=conn,
            table_name=table_name,
            how="append",
            schema=schema,
            logger=logger,
        )


@task
def add_geometry_column_to_table(
    schema: str = "public", table_name: str = "risques_mvt"
):
    """
    Add geometry column and index
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                ALTER TABLE {q(schema)}.{q(table_name)} 
                    ADD COLUMN IF NOT EXISTS 
                    geom geometry(POINT, 2154);
                CREATE INDEX IF NOT EXISTS {q(f"sidx_{table_name}_geom")}
                    ON {q(schema)}.{q(table_name)} USING GIST (geom);
                """
            )
        )


@task
def populate_geom(schema: str = "public", table_name: str = "risques_mvt"):
    """
    Populate the geom column with the latitude and longitude columns
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                UPDATE {q(schema)}.{q(table_name)}
                SET geom = ST_Transform(
                    ST_SetSRID(ST_MakePoint(longitude, latitude),
                    4326), 2154)
                WHERE 
                    longitude IS NOT NULL 
                    AND latitude IS NOT NULL
                    ;
                """
            )
        )


@task
def import_mvt_files(
    path: Path, schema: str = "public", table_name: str = "risques_mvt"
):
    files = list_files_at_path(path, r".*mvt.*|.*fichecommunes.*", extension=".csv")
    if not files:
        files = list_files_at_path(path, r".*", extension=".csv")
    logger.info(f"Found {len(files)} files to import")
    for file in files:
        complete_file_path = os.path.join(path, file)
        encode_to_utf8(complete_file_path)
        logger.info(f"Importing file: {file}")
        load_mvt(complete_file_path, schema=schema, table_name=table_name)


@flow
def import_risques_mvt_flow(
    path: Optional[Path] = None,
    department: Optional[str] = None,
    schema: str = "public",
    table_name: str = "risques_mvt",
    recreate: bool = False,
):
    """
    Import des données de mouvements de terrain.
    Si path n'est pas fourni, le département est utilisé
    pour télécharger le CSV depuis Géorisques.
    """
    if path is None and department is None:
        raise ValueError("Le chemin du répertoire ou le département doit être fourni.")

    create_table_mvt(schema=schema, table_name=table_name, recreate=recreate)
    add_geometry_column_to_table(schema=schema, table_name=table_name)

    if path is None:
        logger.info(f"Downloading MVT data for department {department}")
        url = f"https://www.georisques.gouv.fr/webappReport/ws/mvmt/departements/{department}/fichecommunes.csv"
        target_dir = TEMP_DIR / "georisques/mvt" / department
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"mvt_{department}.csv"

        response = requests.get(url)
        if response.status_code == 200:
            with open(target_file, "wb") as f:
                f.write(response.content)
            logger.info(f"Successfully downloaded to {target_file}")
            encode_to_utf8(str(target_file))
            load_mvt(str(target_file), schema=schema, table_name=table_name)
        else:
            logger.error(
                f"Failed to download MVT data. Status code: {response.status_code}"
            )
            return
    else:
        logger.info(f"Importing MVT files from {path}")
        import_mvt_files(path, schema=schema, table_name=table_name)

    populate_geom(schema=schema, table_name=table_name)
