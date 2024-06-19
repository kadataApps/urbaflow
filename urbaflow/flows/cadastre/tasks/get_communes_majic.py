import os

from logging_config import logger
from utils.dbutils import pg_connection
from utils.config import db_schema, config


def get_imported_communes_from_file():
    """
    Récupération de la liste des communes dans le fichier communes.txt
    """
    filename = os.path.join(os.getcwd(), "temp/communes.txt")
    return config(filename, section="communes")


def get_imported_communes_from_postgres():
    """
    Récupération de la liste des communes importées dans postgis via l'import MAJIC
    """
    logger.info("Liste des code communes importés dans MAJIC")
    schema = db_schema()["schema"]
    select_communes_query = (
        "SELECT '[''' || string_agg(communes, ''',''') ||''']' "
        "FROM("
        "SELECT distinct ccodep || ccocom as communes "
        "FROM %s.parcelle) t;" % schema
    )
    conn = pg_connection()
    conn.execute_sql(select_communes_query)
    communes = conn.cur.fetchone()[0]
    conn.close_connection()
    return communes


def write_communes_to_file():
    communes = get_imported_communes_from_postgres()
    logger.info("Liste des communes")
    logger.info(communes)
    file = open(os.path.join(os.getcwd(), "temp/communes.txt"), "w")
    file.write("[communes]\n")
    file.write("communes = ")
    if communes is not None:
        file.write(communes)
