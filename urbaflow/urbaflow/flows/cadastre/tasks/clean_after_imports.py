import shutil
import os

from utils.dbutils import pg_connection
from utils.config import db_schema


def clean_temp_dir():
    shutil.rmtree(os.path.join(os.getcwd(), "/temp"), ignore_errors=True)


def clean_db():
    schema = db_schema()

    sql = "DROP SCHEMA %s CASCADE;" % schema
    conn = pg_connection()
    conn.execute_sql(sql)
    conn.commit()
    conn.close_connection()
