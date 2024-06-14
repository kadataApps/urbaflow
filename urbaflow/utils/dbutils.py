#!/usr/bin/python
import psycopg2
import os
import sys

from logging_config import logger
from .config import db_config, db_schema


def import_shapefile(
    file: str,
    table: str,
    schema: str,
    destination_srs: str = "EPSG:2154",
    source_srs: str = "EPSG:4326",
):
    params = db_config()
    # {'host': 'localhost', 'database': 'local_test', 'user': 'postgres', 'password': 'postgres', 'port': '5433'}
    params["table"] = table
    params["file"] = file
    params["schema"] = schema

    # command = ('ogr2ogr -f "PostgreSQL" '
    #     'PG:"host=%(host)s port=%(port)s user=%(user)s password=%(password)s dbname=%(database)s"'
    #     '"%(file)s" -nln %(table)s -append -update -skipfailures -a_srs "EPSG:4326"'
    #     % params)
    password_string = (
        f'PGPASSWORD=\'{ params["password"] }\'' if params["password"] != "" else ""
    )
    command = (
        f'{ password_string } '
        f'ogr2ogr -f "PostgreSQL" '
        f'PG:"host={params["host"]} port={params["port"]} user={params["user"]} dbname={params["database"]} " '
        f'"{params["file"]}" -nln {params["schema"]}.{params["table"]} -append -update -skipfailures -s_srs "{source_srs}" -t_srs "{destination_srs}" -nlt "PROMOTE_TO_MULTI"'
    )
    logger.info(command)
    try:
        os.system(command)
    except OSError as e:
        logger.error(e)


class importGeoJSON(object):
    def importFile(self, file, table):
        params = db_config()
        schema = db_schema()["schema"]
        # {'host': 'localhost', 'database': 'local_test', 'user': 'postgres', 'password': 'postgres', 'port': '5433'}
        params["table"] = table
        params["file"] = file
        params["schema"] = schema

        # command = ('ogr2ogr -f "PostgreSQL" '
        #     'PG:"host=%(host)s port=%(port)s user=%(user)s password=%(password)s dbname=%(database)s"'
        #     '"%(file)s" -nln %(table)s -append -update -skipfailures -a_srs "EPSG:4326"'
        #     % params)
        password_string = (
            f'PGPASSWORD=\'{ params["password"] }\'' if params["password"] != "" else ""
        )
        command = (
            f'{ password_string } '
            f'ogr2ogr -f "PostgreSQL" '
            f'PG:"host={params["host"]} port={params["port"]} user={params["user"]} dbname={params["database"]} " '
            f'"{params["file"]}" -nln {params["schema"]}.{params["table"]} -append -update -skipfailures -a_srs "EPSG:4326" -nlt "PROMOTE_TO_MULTI"'
        )
        logger.info(command)
        try:
            os.system(command)
        except OSError as e:
            logger.error(e)


class pg_connection(object):
    """Connect to the PostgreSQL database server"""

    conn = None
    cur = None

    def __init__(self):
        self.openConnection()
        self.setSearchPathToImportSchema()

    def openConnection(self):
        try:
            # read connection parameters
            params = db_config()

            # connect to the PostgreSQL server
            logger.info("Connecting to the PostgreSQL database...")
            self.conn = psycopg2.connect(**params)

            # create a cursor
            self.cur = self.conn.cursor()

        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(error)
            if self.conn is not None:
                self.conn.close()
                logger.info("Database connection closed after error.")
            sys.exit()

    def commit(self):
        if self.conn is not None:
            self.conn.commit()
            logger.info("Transaction commited.")

    def close_connection(self):
        if self.conn is not None:
            self.conn.close()
            logger.info("Database connection closed.")

    def execute_sql(self, sql, *args):
        """
        sql queries are not commited.
        Call connexion.commit() to commit the transaction
        before calling connexion.close_connection()
        """
        self.cur.execute(sql, *args)

    def execute_script(self, sqlscript_path):
        """
        Scripts are commited automatically but connexion remains open.
        """
        sqlFile = open(sqlscript_path, "r")
        self.cur.execute(sqlFile.read())
        self.commit()

    def setSearchPathToImportSchema(self):
        """
        Set the search_path parameter in postgis database to [importSchema], public, pg_catalog.
        Creates [importSchema] if it doesn't exists
        """
        schema = db_schema()["schema"]
        schemaDoesExistsSql = (
            "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='%s')" % schema
        )
        self.execute_sql(schemaDoesExistsSql)
        schemaDoesExists = self.cur.fetchone()
        if not schemaDoesExists[0]:
            logger.info("Create schema %s" % schema)
            self.execute_sql("CREATE SCHEMA %s" % schema)
        prefix = 'SET search_path = "%s", public, pg_catalog;' % schema
        self.execute_sql(prefix)
        logger.info("Working Schema: %s" % schema)

    def set_search_path_to_public(self):
        """
        Set the search_path parameter in postgis database to 'public, pg_catalog'
        """
        sql = "SET search_path = public, pg_catalog;"
        self.execute_sql(sql)

    def getPostgreSQLversion(self):
        self.cur.execute("SELECT version()")
        # display the PostgreSQL database server version
        db_version = self.cur.fetchone()
        logger.info(db_version)
        # close the communication with the PostgreSQL
        self.cur.close()
