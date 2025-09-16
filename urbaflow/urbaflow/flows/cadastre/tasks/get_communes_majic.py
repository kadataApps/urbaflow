from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import read_query
from shared_tasks.logging_config import get_logger
from shared_tasks.config import db_schema


logger = get_logger(__name__)


def get_imported_communes_from_postgres():
    """
    Récupération de la liste des communes importées dans postgis via l'import MAJIC
    """
    logger.info("Liste des code communes importés dans MAJIC")
    schema = db_schema()
    select_communes_query = (
        "SELECT distinct ccodep || ccocom as code_insee " "FROM %s.parcelle;" % schema
    )

    e = create_engine()
    with e.connect() as conn:
        communes = read_query(connection=conn, query=select_communes_query)
    return communes
