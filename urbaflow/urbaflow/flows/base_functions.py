from prefect import flow
from shared_tasks.config import QUERIES_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)


@flow
def install_base_functions_flow() -> None:
    """Installe les fonctions polygonales dans public en une seule transaction."""
    scripts_directory = QUERIES_DIR / "base_functions"
    engine = create_engine()
    try:
        with engine.begin() as connection:
            for script_name in (
                "PolygonalMakeValid.sql",
                "PolygonalIntersection.sql",
            ):
                logger.info("Installation de la fonction %s", script_name)
                run_sql_script(
                    connection=connection,
                    sql_filepath=scripts_directory / script_name,
                )
    finally:
        engine.dispose()

    logger.info("Installation des fonctions polygonales terminée.")
