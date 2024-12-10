import os

from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import logger


def execute_init_cadastre():
    """
    Création table cadastre_parcelles pour import du cadastre
    (Si la table n'existe pas)
    """
    logger.info("Création table cadastre_parcelles")
    script_path_create = os.path.join(
        os.getcwd(),
        "temp/sql/traitements/cadastre/0-initialisation_cadastre_parcelle.sql",
    )
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
        logger.info("La table cadastre_parcelles a été créée si nécessaire.")


def execute_format_cadastre():
    """
    Ajout et mise à jour colonne geo_parcelles
    sur cadastre_parcelles pour jointure
    avec MAJIC
    """
    logger.info("Ajout/Mise à jour geo_parcelles sur table cadastre_parcelles")
    script_path = os.path.join(
        os.getcwd(), "temp/sql/traitements/cadastre/1-traitement_cadastre_parcelles.sql"
    )
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path, connection=conn)
        logger.info("Table cadastre_parcelles mise à jour.")


def execute_init_bati():
    """
    Création table cadastre_bati pour import du cadastre
    (Si la table n'existe pas)
    """
    logger.info("Création table cadastre_bati")
    script_path = os.path.join(
        os.getcwd(), "temp/sql/traitements/bati/0-initialisation_cadastre_bati.sql"
    )
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path, connection=conn)
        logger.info("La table cadastre_bati a été créée si nécessaire.")
