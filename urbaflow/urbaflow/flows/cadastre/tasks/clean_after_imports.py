import os
import shutil
from pathlib import Path

from shared_tasks.config import TEMP_DIR, majic_schema
from shared_tasks.db_engine import create_engine, quote_identifier
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import get_logger


def clean_temp_dir():
    """Supprime les scripts et téléchargements temporaires de ce traitement."""
    for directory in (TEMP_DIR / "sql", Path(os.getcwd()) / "temp/downloads"):
        if directory.exists():
            shutil.rmtree(directory)


def clean_db():
    """Supprime uniquement le schéma de travail MAJIC et son contenu."""
    schema = majic_schema()
    get_logger().info(f"Suppression du schéma de travail MAJIC : {schema}")
    sql = f"DROP SCHEMA IF EXISTS {quote_identifier(schema)} CASCADE;"
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=sql, connection=conn)
