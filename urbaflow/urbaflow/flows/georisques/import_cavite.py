# %%
import logging
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import DDL

from shared_tasks.etl_gpd_utils import load
from shared_tasks.db_engine import create_engine
from shared_tasks.file_utils import encode_to_utf8, list_files_at_path


logger = logging.getLogger(__name__)


def create_table_cavite(
    schema: str = "public", table_name: str = "risques_cavite", recreate: bool = True
):
    """
    Create the table in the database
    """
    e = create_engine()
    with e.begin() as conn:
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {schema}.{table_name}"))
            logger.info(f"Dropping table {schema}.{table_name} if it exists")

        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.{table_name} (
                    id text PRIMARY KEY,
                    num_cavite text,
                    indice_bss text,
                    designation_bss text,
                    nature_cavite text,
                    type_cavite text,
                    type_cavite_appauvri text,
                    nom_cavite text,
                    statut text,
                    confidentialite text,
                    raison_confidentialite text,
                    organisme_chx_confidentialite text,
                    reperage_geographique text,
                    positionnement text,
                    positionnement_appauvri text,
                    source_coordonnees text,
                    precision_xy text,
                    date_validite text,
                    auteur_description text,
                    date_maj_cavite text,
                    lambert_ouvrage text,
                    x_ouvrage numeric,
                    y_ouvrage numeric,
                    z_ouvrage numeric,
                    xouvl2e numeric,
                    youvl2e numeric,
                    num_insee text,
                    commentaires text,
                    cavite_associee text,
                    c_user_saisie text,
                    c_date_saisie text,
                    c_user_modif text,
                    date_validation_saisie text,
                    date_validation_diffusion text,
                    user_validation_saisie text,
                    user_validation_diffusion text,
                    statut_validation text,
                    dangerosite text
                )
                """
            )
        )
        logger.info(f"Created table {schema}.{table_name} if it did not exist")


def load_cavite(file, schema="public", table_name="risques_cavite"):
    """
    Import des données de mouvements de terrain à partir d'un fichier CSV.
    Les données sont importées par défaut dans la table "risques_cavite" du schéma "public".
    """
    logger.info("Importing file: " + file)

    cavite_df = pd.read_csv(file, sep=";", encoding="UTF-8", low_memory=False)
    ## renommage des colonnes pour correspondre au schéma de la table
    ## (snake_case, clarification des noms)
    cavite_df = cavite_df.rename(
        columns={
            "numCavite": "num_cavite",
            "indiceBSS": "indice_bss",
            "designationBSS": "designation_bss",
            "natureCavite": "nature_cavite",
            "typeCavite": "type_cavite",
            "typeCaviteAppauvri": "type_cavite_appauvri",
            "nomCavite": "nom_cavite",
            "statut": "statut",
            "confidentialite": "confidentialite",
            "raisonConfidentialite": "raison_confidentialite",
            "organismeChxConfidentialite": "organisme_chx_confidentialite",
            "reperageGeographique": "reperage_geographique",
            "positionnement": "positionnement",
            "positionnementAppauvri": "positionnement_appauvri",
            "sourceCoordonnees": "source_coordonnees",
            "precisionXY": "precision_xy",
            "dateValidite": "date_validite",
            "auteurDescription": "auteur_description",
            "dateMajCavite": "date_maj_cavite",
            "lambertOuvrage": "lambert_ouvrage",
            "xOuvrage": "x_ouvrage",
            "yOuvrage": "y_ouvrage",
            "zOuvrage": "z_ouvrage",
            "xouvl2e": "xouvl2e",
            "youvl2e": "youvl2e",
            "numInsee": "num_insee",
            "commentaires": "commentaires",
            "caviteAssociee": "cavite_associee",
            "cUserSaisie": "c_user_saisie",
            "cDateSaisie": "c_date_saisie",
            "cUserModif": "c_user_modif",
            "dateValidationSaisie": "date_validation_saisie",
            "dateValidationDiffusion": "date_validation_diffusion",
            "userValidationSaisie": "user_validation_saisie",
            "userValidationDiffusion": "user_validation_diffusion",
            "statutValidation": "statut_validation",
            "dangerosite": "dangerosite",
        }
    )

    # extraction des colonnes à importer
    cavite_df = cavite_df[
        [
            "id",
            "num_cavite",
            "indice_bss",
            "designation_bss",
            "nature_cavite",
            "type_cavite",
            "type_cavite_appauvri",
            "nom_cavite",
            "statut",
            "confidentialite",
            "raison_confidentialite",
            "organisme_chx_confidentialite",
            "reperage_geographique",
            "positionnement",
            "positionnement_appauvri",
            "source_coordonnees",
            "precision_xy",
            "date_validite",
            "auteur_description",
            "date_maj_cavite",
            "lambert_ouvrage",
            "x_ouvrage",
            "y_ouvrage",
            "z_ouvrage",
            "xouvl2e",
            "youvl2e",
            "num_insee",
            "commentaires",
            "cavite_associee",
            "c_user_saisie",
            "c_date_saisie",
            "c_user_modif",
            "date_validation_saisie",
            "date_validation_diffusion",
            "user_validation_saisie",
            "user_validation_diffusion",
            "statut_validation",
            "dangerosite",
        ]
    ]

    e = create_engine()
    with e.begin() as conn:
        load(
            cavite_df,
            connection=conn,
            table_name=table_name,
            how="append",
            schema=schema,
            logger=logger,
        )

    logger.info(f"Import terminé pour le fichier : {file}")
    row_count = len(cavite_df)
    logger.info(f"Nombre de lignes importées : {row_count}")


def add_geometry_column_to_table(schema="public", table_name="risques_cavite"):
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


def populate_geom(schema="public", table_name="risques_cavite"):
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
                    ST_SetSRID(ST_MakePoint(xouvl2e, youvl2e),
                    27572), 2154)
                WHERE 
                    xouvl2e IS NOT NULL 
                    AND youvl2e IS NOT NULL
                    ;
                """
            )
        )


def import_cavite_files(path: Path):
    files = list_files_at_path(path, r"^cavite.*", extension=".csv")
    logger.info(f"Found {len(files)} files to import")
    for file in files:
        complete_file_path = os.path.join(path, file)
        encode_to_utf8(complete_file_path)
        logger.info(f"Importing file: {file}")
        load_cavite(complete_file_path)


def import_risques_cavite_flow(
    path: Path,
    department: str,
    schema="public",
    table_name="risques_cavite",
    recreate: bool = True,
):
    """
    Flow to import cavite data from georisques.gouv.fr for a given department.

    Parameters
    ----------
    path : Path
        Path to the directory where the cavite files will be stored. If provided,
        no download will be performed. department parameter will be ignored.
    department : str
        Department code (e.g., "76" for Seine-Maritime).
    schema : str, optional
        Database schema name, by default "public".
    table_name : str, optional
        Database table name, by default "risques_cavite".
    recreate : bool, optional
        Whether to drop and recreate the table if it exists, by default True.
    """

    if path is None and department is None:
        logger.error("Either path or department must be provided")
        return

    create_table_cavite(schema=schema, table_name=table_name, recreate=recreate)
    add_geometry_column_to_table(schema=schema, table_name=table_name)

    if path is None:
        logger.info(f"Downloading cavite data for department {department}")
        source = f"https://georisques.gouv.fr/webappReport/ws/cavites/departements/{department}/fichecommunes.csv"
        load_cavite(source, schema=schema, table_name=table_name)

    else:
        if not path.exists():
            logger.info(f"Path {path} does not exist.")
            return
        logger.info(f"Using existing files in {path}")
        import_cavite_files(path)

    populate_geom(schema=schema, table_name=table_name)
