import os
from pathlib import Path

import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import load
from shared_tasks.file_utils import encode_to_utf8, list_files_at_path
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL

# Les données CASIAS sont disponibles sur le site Géorisques
# Exemple : https://www.georisques.gouv.fr/webappReport/ws/infosols/casias/_search?isExport=true&codeDepartement=85

logger = get_logger(__name__)


@task
def create_table_casias(
    schema: str = "public", table_name: str = "risques_casias", recreate: bool = True
):
    """
    Crée la table PostGIS pour les données CASIAS dans la base de données.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {q(schema)}.{q(table_name)}"))
            logger.info(f"Suppression de la table {schema}.{table_name} si elle existe")

        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {q(schema)}.{q(table_name)} (
                    code_metier text PRIMARY KEY,
                    nom_inventaire text,
                    code_inventaire text,
                    nom_etablissement text,
                    code_siret text,
                    adresse text,
                    code_postal text,
                    code_insee text,
                    nom_commune text,
                    code_departement text,
                    nom_departement text,
                    code_region text,
                    nom_region text,
                    etat_activite text,
                    code_naf text,
                    activite_principale text,
                    nature_localisation text,
                    x_wgs84 numeric,
                    y_wgs84 numeric,
                    fiche_risque text
                )
                """
            )
        )
        logger.info(
            f"Table {schema}.{table_name} créée si elle n'existait pas auparavant"
        )


@task
def load_casias(file: str, schema: str = "public", table_name: str = "risques_casias"):
    """
    Importe les données CASIAS à partir d'un fichier CSV.
    Les données sont insérées dans la table du schéma spécifié.
    """
    logger.info("Importation du fichier : %s", file)

    casias_df = pd.read_csv(file, sep=";", encoding="UTF-8", low_memory=False)

    # Conversion du code_metier en chaîne de caractères et dédoublonnage
    casias_df["code_metier"] = casias_df["code_metier"].astype(str)
    casias_df = casias_df.drop_duplicates(subset=["code_metier"])

    # Extraction et ordonnancement des colonnes à importer
    expected_columns = [
        "code_metier",
        "nom_inventaire",
        "code_inventaire",
        "nom_etablissement",
        "code_siret",
        "adresse",
        "code_postal",
        "code_insee",
        "nom_commune",
        "code_departement",
        "nom_departement",
        "code_region",
        "nom_region",
        "etat_activite",
        "code_naf",
        "activite_principale",
        "nature_localisation",
        "x_wgs84",
        "y_wgs84",
        "fiche_risque",
    ]
    available_columns = [col for col in expected_columns if col in casias_df.columns]
    casias_df = casias_df[available_columns]

    e = create_engine()
    with e.begin() as conn:
        load(
            casias_df,
            connection=conn,
            table_name=table_name,
            how="append",
            schema=schema,
            logger=logger,
        )


@task
def add_geometry_column_to_table(
    schema: str = "public", table_name: str = "risques_casias"
):
    """
    Ajoute la colonne geom (Lambert 93, EPSG:2154) et l'index GIST associé.
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
def populate_geom(schema: str = "public", table_name: str = "risques_casias"):
    """
    Alimente la colonne geom à partir des coordonnées x_wgs84 et y_wgs84 (EPSG:4326).
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                UPDATE {q(schema)}.{q(table_name)}
                SET geom = ST_Transform(
                    ST_SetSRID(ST_MakePoint(x_wgs84, y_wgs84),
                    4326), 2154)
                WHERE 
                    x_wgs84 IS NOT NULL 
                    AND y_wgs84 IS NOT NULL
                    ;
                """
            )
        )


@task
def import_casias_files(
    path: Path, schema: str = "public", table_name: str = "risques_casias"
):
    """
    Recherche et importe les fichiers CSV CASIAS présents dans un répertoire.
    """
    files = list_files_at_path(
        path, r".*casias.*|.*result.*|.*fichecommunes.*", extension=".csv"
    )
    if not files:
        files = list_files_at_path(path, r".*", extension=".csv")
    logger.info("Trouvé %d fichier(s) à importer", len(files))
    for file in files:
        complete_file_path = os.path.join(path, file)
        encode_to_utf8(complete_file_path)
        logger.info("Importation du fichier : %s", file)
        load_casias(complete_file_path, schema=schema, table_name=table_name)


@flow
def import_risques_casias_flow(
    path: Path | None = None,
    department: str | None = None,
    db_schema: str = "public",
    table_name: str = "risques_casias",
    recreate: bool = False,
):
    """
    Flow d'importation des données Géorisques CASIAS.
    Si le répertoire (path) n'est pas fourni, les données
    sont téléchargées pour le département spécifié.
    """
    if path is None and department is None:
        raise ValueError("Le chemin du répertoire ou le département doit être fourni.")

    create_table_casias(schema=db_schema, table_name=table_name, recreate=recreate)
    add_geometry_column_to_table(schema=db_schema, table_name=table_name)

    if path is None:
        logger.info(
            "Téléchargement des données CASIAS pour le département %s", department
        )
        url = (
            "https://www.georisques.gouv.fr/webappReport/ws/infosols/casias/_search"
            f"?isExport=true&codeDepartement={department}"
        )
        target_dir = TEMP_DIR / "georisques/casias" / department
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"casias_{department}.csv"

        response = requests.get(url)
        if response.status_code == 200:
            with open(target_file, "wb") as f:
                f.write(response.content)
            logger.info("Téléchargement réussi dans %s", target_file)
            encode_to_utf8(str(target_file))
            load_casias(str(target_file), schema=db_schema, table_name=table_name)
        else:
            logger.error(
                "Échec du téléchargement des données CASIAS. Code de statut : %d",
                response.status_code,
            )
            return
    else:
        logger.info("Importation des fichiers CASIAS depuis le répertoire %s", path)
        import_casias_files(path, schema=db_schema, table_name=table_name)

    populate_geom(schema=db_schema, table_name=table_name)
