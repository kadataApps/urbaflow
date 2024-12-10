import shutil
import os

from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.config import db_schema


def clean_temp_dir():
    shutil.rmtree(os.path.join(os.getcwd(), "/temp"), ignore_errors=True)


def clean_db():
    schema = db_schema()

    sql = "DROP SCHEMA %s CASCADE;" % schema
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=sql, connection=conn)
