from shared_tasks.config import majic_schema
from shared_tasks.db_engine import create_engine, quote_identifier
from shared_tasks.db_sql_utils import read_query
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)


def get_imported_communes_from_postgres():
    """
    Récupération de la liste des communes importées dans postgis via l'import MAJIC
    """
    logger.info("Liste des code communes importés dans MAJIC")
    schema = majic_schema()
    select_communes_query = (
        "SELECT distinct ccodep || ccocom as code_insee "
        f"FROM {quote_identifier(schema)}.parcelle;"
    )

    e = create_engine(schema=schema)
    with e.connect() as conn:
        communes = read_query(connection=conn, query=select_communes_query)
    return communes
