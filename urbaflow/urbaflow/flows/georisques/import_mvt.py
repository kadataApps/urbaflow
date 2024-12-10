# %%
import os
from pathlib import Path
import pandas as pd
from prefect import flow, get_run_logger, task
from sqlalchemy import DDL

from shared_tasks.etl_gpd_utils import load
from shared_tasks.db_engine import create_engine
from shared_tasks.file_utils import encode_to_utf8, list_files_at_path

# %%


@task
def create_table_mvt(schema="public", table_name="risques_mvt"):
    """
    Create the table in the database
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.{table_name} (
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
def load_mvt(file, schema="public", table_name="risques_mvt"):
    """
    Import des données de mouvements de terrain à partir d'un fichier CSV.
    Les données sont importées par défaut dans la table "risques_mvt" du schéma "public".
    """
    logger = get_run_logger()
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
            how="replace",
            schema=schema,
            logger=logger,
        )


@task
def add_geometry_column_to_table(schema="public", table_name="risques_mvt"):
    """
    Add geometry column and index
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                f"""
                ALTER TABLE {schema}.{table_name} 
                    ADD COLUMN IF NOT EXISTS 
                    geom geometry(POINT, 2154);
                CREATE INDEX IF NOT EXISTS sidx_{table_name}_geom
                    ON {schema}.{table_name} USING GIST (geom);
                """
            )
        )


@task
def populate_geom(schema="public", table_name="risques_mvt"):
    """
    Populate the geom column with the latitude and longitude columns
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                f"""
                UPDATE {schema}.{table_name}
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
def import_mvt_files(path: Path):
    logger = get_run_logger()
    files = list_files_at_path(path, r"^mvt.*", extension=".csv")
    logger.info(f"Found {len(files)} files to import")
    for file in files:
        complete_file_path = os.path.join(path, file)
        encode_to_utf8(complete_file_path)
        logger.info(f"Importing file: {file}")
        load_mvt(complete_file_path)


@flow(name="import risques mvt")
def import_risques_mvt_flow(path: Path):
    logger = get_run_logger()
    create_table_mvt()
    add_geometry_column_to_table()
    logger.info(f"Importing files from {path}")
    import_mvt_files(path)
    populate_geom()
