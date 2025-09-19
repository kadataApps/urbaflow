from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import get_logger
from shared_tasks.config import QUERIES_DIR


logger = get_logger()


def flow_create_unites_foncieres():
    """
    Execute dans postgis les scripts permettant de
    créer les unités foncières
    """

    logger.info("Execution des scripts de création des unités foncières")
    script_path = QUERIES_DIR / "core/dim_unites_foncieres.sql"

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path, connection=conn)
    logger.info("Création des unités foncières terminée.")
