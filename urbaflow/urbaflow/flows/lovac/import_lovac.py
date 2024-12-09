# %%
from pathlib import Path
from prefect import task, flow
import pandas as pd
from sqlalchemy import DDL, text

from urbaflow.logging_config import logger
from urbaflow.shared_tasks.generic_tasks import load
from urbaflow.urbaflow.utils.db_engine import create_engine

# https://doc-datafoncier.cerema.fr/doc/lovac/
# https://doc-datafoncier.cerema.fr/doc/guide/lovac


@task
def find_lovac_files(dirname: Path) -> list[Path]:
    """
    Find all files in the directory that match the pattern 'LOVAC_*.CSV|csv'
    """
    # Example filename: LOVAC22_170_20003647300011_G863_23103.CSV
    # filename pattern is "LOVAC*.CSV"
    csv_files = list(dirname.glob("LOVAC*.CSV")) + list(dirname.glob("LOVAC_*.csv"))
    if len(csv_files) == 0:
        raise FileNotFoundError(
            f"No files found in {dirname} that match the pattern 'LOVAC_*.CSV|csv'"
        )
    return csv_files


@task
def extract_lovac_data(file: Path) -> pd.DataFrame:
    """
    Extract the data from the file
    """
    colmun_dtypes_spec = {
        "SIRET DESTINATAIRE": "str",
        "CODE EPCI": "str",
        "SIRET EPCI": "str",
        "ANNEE": "str",
        "CODE DSF": "str",
        "CODE COMMUNE": "str",
        "CODE VOIE": "str",
        "PREFIXE DE SECTION": "str",
        "SECTION CADASTRALE": "str",
        "NUMERO DE PLAN": "str",
        "NUMERO DE BATIMENT": "str",
        "NUMERO D ENTREE/D ESCALIER": "str",
        "ETAGE": "str",
        "NUMERO DE PORTE": "str",
        "NUMERO DE VOIRIE": "str",
        "CODE INDICE DE REPETITION": "str",
        "ADRESSE": "str",
        "CODE POSTAL": "str",
        "LIBELLE COMMUNE": "str",
        "PROPRIETAIRE": "str",
        "INVARIANT DU LOCAL": "str",
        "CODE NATURE DU LOCAL": "str",
        "CODE AFFECTATION DU LOCAL": "str",
        "CATEGORIE REVISEE": "str",
        "VALEUR LOCATIVE REVISEE DU DESCRIPTIF": "str",
        "CODE SIE": "str",
    }

    df = pd.read_csv(file, sep=";", dtype=colmun_dtypes_spec)
    logger.info(f"Loaded {len(df)} rows from {file}")
    df["idparcelle_geom"] = (
        df["CODE DSF"]
        + df["CODE COMMUNE"].str.zfill(3)
        + df["PREFIXE DE SECTION"].fillna("").str.zfill(3)
        + df["SECTION CADASTRALE"]
        + df["NUMERO DE PLAN"].str.zfill(4)
    )
    result_df = df.groupby("idparcelle_geom").size().reset_index(name="nblovac")
    return result_df


@task
def create_table_lovac():
    """
    Create the table in the database
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                CREATE TABLE IF NOT EXISTS public.lovac (
                    idparcelle_geom text PRIMARY KEY,
                    nblovac INTEGER
                )
                """
            )
        )


@task
def load_lovac_data(data: pd.DataFrame):
    """
    Load the data into the database
    """
    e = create_engine()
    with e.begin() as conn:
        load(
            data,
            connection=conn,
            table_name="lovac",
            how="replace",
            schema="public",
            logger=logger,
        )


@task
def transform_lovac_data():
    """
    Add geometry to lovac table
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                ALTER TABLE public.lovac
                ADD COLUMN IF NOT EXISTS geom geometry(MULTIPOLYGON, 2154);
                CREATE INDEX IF NOT EXISTS sidx_lovac_geom ON public.lovac USING GIST (geom);
                """
            )
        )
        logger.info("Added geom column to lovac table")
        conn.execute(
            text(
                """
                UPDATE public.lovac
                SET geom = parcelle.geom
                FROM public.parcellaire_france as parcelle
                WHERE lovac.idparcelle_geom = parcelle.idparcelle_geom
                """
            )
        )
        logger.info("Updated geom column in lovac table from parcellaire_france table")
    return


@task
def create_extract_lovac_table():
    """
    Create the table in the database
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS extract_lovac (
                SELECT nom_site,
                  nvac || '/'|| nlocal ||' logements vacants depuis '||debvac|| coalesce('  (dont ' || nvach || ' log. vac. de + de 2 ans depuis '||debvach||')', '') as commentaire,
                  origine_reperage,
                  echeance,
                  vocation,
                  geom
                  FROM (
                  SELECT 'Logement vacant' as nom_site, 

                    'Vacance FF/LOVAC' as origine_reperage, 
                    'A valider' as echeance,
                    'Habitat' as vocation,
                    st_multi(p.geom) geom,
                    p.nlocal as nlocal,
                    count(distinct l.id) nvac,
                    count(distinct l1.id) nvach,
                    min(l.debutvacan) debvac,
                    min(l1.debutvacan) as debvach
                  FROM :schema.parcellaire p left join :schema.:lovac_ex_table_name l
                    on (p.geom && l.geom AND st_within(l.geom, p.geom)) 
                    left join :schema.lovac_fil_table_name l1 on (p.geom && l1.geom AND st_within(l1.geom, p.geom)) 
                  WHERE nlogh > 1 AND nloghvac = nlogh 
                  group by 1, 2, 3, 4, 5,6  ) t
                """
            )
        )


@flow(name="Import Locomvac")
def import_lovac_flow(dirname: Path):
    logger.info(f"Importing lovac data from {dirname}")
    create_table_lovac()
    files = find_lovac_files(dirname)
    for file in files:
        data = extract_lovac_data(file)
        load_lovac_data(data)
