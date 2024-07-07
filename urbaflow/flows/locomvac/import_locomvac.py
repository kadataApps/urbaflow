# %%
from pathlib import Path
from prefect import task, flow
import pandas as pd
from sqlalchemy import DDL, text

from urbaflow.logging_config import logger 
from urbaflow.shared_tasks.generic_tasks import load
from urbaflow.utils.db_config import create_engine

@task
def find_locomvac_files(dirname: Path)->list[Path]:
    """
    Find all files in the directory that match the pattern 'LOCOMVAC_*.CSV|csv'
    """
    # Example filename: LOCOMVAC22_170_20003647300011_G863_23103.CSV
    # filename pattern is "LOCOMVAC*.CSV"
    csv_files = list(dirname.glob("LOCOMVAC*.CSV")) + list(dirname.glob("LOCOMVAC_*.csv"))
    if len(csv_files) == 0:
        raise FileNotFoundError(f"No files found in {dirname} that match the pattern 'LOCOMVAC_*.CSV|csv'")
    return csv_files

@task
def extract_locomvac_data(file: Path)->pd.DataFrame:
    """
    Extract the data from the file
    """
    colmun_dtypes_spec = {
        'SIRET DESTINATAIRE': 'str',
        'CODE EPCI': 'str',
        'SIRET EPCI': 'str',
        'ANNEE': 'str',
        'CODE DSF': 'str',
        'CODE COMMUNE': 'str',
        'CODE VOIE': 'str',
        'PREFIXE DE SECTION': 'str',
        'SECTION CADASTRALE': 'str',
        'NUMERO DE PLAN': 'str',
        'NUMERO DE BATIMENT': 'str',
        'NUMERO D ENTREE/D ESCALIER': 'str',
        'ETAGE': 'str',
        'NUMERO DE PORTE': 'str',
        'NUMERO DE VOIRIE': 'str',
        'CODE INDICE DE REPETITION': 'str',
        'ADRESSE': 'str',
        'CODE POSTAL': 'str',
        'LIBELLE COMMUNE': 'str',
        'PROPRIETAIRE': 'str',
        'INVARIANT DU LOCAL': 'str',
        'CODE NATURE DU LOCAL': 'str',
        'CODE AFFECTATION DU LOCAL': 'str',
        'CATEGORIE REVISEE': 'str',
        'VALEUR LOCATIVE REVISEE DU DESCRIPTIF': 'str',
        'CODE SIE': 'str'
    }

    df = pd.read_csv(file, sep=';', dtype=colmun_dtypes_spec)
    logger.info(f"Loaded {len(df)} rows from {file}")
    df["idparcelle_geom"] = df["CODE DSF"] + df["CODE COMMUNE"].str.zfill(3) + df['PREFIXE DE SECTION'].fillna("").str.zfill(3) + df["SECTION CADASTRALE"] + df["NUMERO DE PLAN"].str.zfill(4)
    result_df = df.groupby('idparcelle_geom').size().reset_index(name='nblocomvac')
    return result_df
    

@task
def create_table_locomvac():
    """
    Create the table in the database
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                CREATE TABLE IF NOT EXISTS public.locomvac (
                    idparcelle_geom text PRIMARY KEY,
                    nblocomvac INTEGER
                )
                """
            )
        )

@task
def load_locomvac_data(data: pd.DataFrame):
    """
    Load the data into the database
    """
    e = create_engine()
    with e.begin() as conn:
        load(data,
            connection=conn,
            table_name="locomvac",
            how="replace",
            schema="public",
            logger=logger
        )

@task
def transform_locomvac_data():
    """
    Add geometry to locomvac table
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                ALTER TABLE public.locomvac
                ADD COLUMN IF NOT EXISTS geom geometry(MULTIPOLYGON, 2154);
                CREATE INDEX IF NOT EXISTS sidx_locomvac_geom ON public.locomvac USING GIST (geom);
                """
            )
        )
        logger.info("Added geom column to locomvac table")
        conn.execute(
            text(
                """
                UPDATE public.locomvac
                SET geom = parcelle.geom
                FROM public.parcellaire_france as parcelle
                WHERE locomvac.idparcelle_geom = parcelle.idparcelle_geom
                """
            )
        )
        logger.info("Updated geom column in locomvac table from parcellaire_france table")
    return


@flow(name="Import Locomvac")
def import_locomvac_flow(dirname: Path):
    logger.info(f"Importing locomvac data from {dirname}")
    create_table_locomvac()
    files = find_locomvac_files(dirname)
    for file in files:
        data = extract_locomvac_data(file)
        load_locomvac_data(data)
