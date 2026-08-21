from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import get_logger


def create_dgfip_topo_tables() -> None:
    """Crée les tables d'adresses alimentées par les entités topographiques DGFiP."""
    logger = get_logger(__name__)
    script_path = TEMP_DIR / "sql/create_dgfip_topo.sql"
    engine = create_engine()
    with engine.begin() as connection:
        run_sql_script(sql_filepath=script_path, connection=connection)
    logger.info("Tables d'adresses DGFiP TOPO créées")


def format_dgfip_topo_data() -> None:
    """Transforme les entités topographiques DGFiP pour les traitements MAJIC."""
    logger = get_logger(__name__)
    script_path = TEMP_DIR / "sql/formatage_dgfip_topo.sql"
    engine = create_engine()
    with engine.begin() as connection:
        run_sql_script(sql_filepath=script_path, connection=connection)
    logger.info("Formatage des entités topographiques DGFiP terminé")