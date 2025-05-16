from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.sql_query_utils import replace_parameters_in_script
from shared_tasks.config import TEMP_DIR
from shared_tasks.logging_config import get_logger


def create_fantoir_tables():
    """
    Création des tables métiers (QgisCadastre) pour import des données  FANTOIR / MAJIC brutes
    """
    logger = get_logger()
    logger.info(
        "Initialisation base de données - tables métiers FANTOIR / MAJIC - cf.QgisCadastre"
    )
    script_path_create = TEMP_DIR / "sql/create_fantoir.sql"
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
    logger.info("Base de données initialisée avec les tables métiers FANTOIR/MAJIC.")


def truncate_fantoir_tables():
    """
    Vide les tables communes et voies avant l'import/formatage avec formatage_fantoir
    """
    sql = "TRUNCATE TABLE voie_france; TRUNCATE TABLE commune_france;"
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=sql, connection=conn)


def format_fantoir_data():
    """
    Execute dans postgis les scripts de formatage des données MAJIC.
    Scripts QgisCadastre (import + formatage MAJIC dans tables métiers)
    + scripts KADATA (calculs indicateurs et croisements)
    """
    logger = get_logger()

    annee = "2019"
    lot = ""
    replace_dict = {"[ANNEE]": annee, "[LOT]": lot}

    script_path = TEMP_DIR / "sql/formatage_fantoir.sql"
    logger.info("formatage Script Fantoir")
    replace_parameters_in_script(script_path, replace_dict)
    logger.info("Script file: %s" % script_path)

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path, connection=conn)
    logger.info("Formatage terminé.")
