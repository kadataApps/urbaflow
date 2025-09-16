import shutil
import os

from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.config import db_schema


def clean_temp_dir():
    shutil.rmtree(os.path.join(os.getcwd(), "/temp"), ignore_errors=True)


def clean_db():
    """
    Drop the temporary schema used for import
    and all its content
    If the schema is "public", do nothing
    """
    schema = db_schema()
    # Do not drop the public schema
    if schema == "public":
        return
    sql = "DROP SCHEMA %s CASCADE;" % schema
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=sql, connection=conn)
