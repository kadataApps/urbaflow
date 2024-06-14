
import shutil
import os

from utils.dbutils import pg_connection
from utils.config import db_schema

def cleanTempDir():
    shutil.rmtree(os.path.join(os.getcwd(), '/temp'), ignore_errors=True)


def cleanDatabase():
    
    schema = db_schema()['schema']

    sql = "DROP SCHEMA %s CASCADE;" % schema
    conn = pg_connection()
    conn.executeSql(sql)
    conn.commit()
    conn.closeConnection()
