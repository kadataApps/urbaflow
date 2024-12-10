#!/usr/bin/python
from prefect import get_run_logger
import psycopg2
import sys

from ..shared_tasks.config import db_config, db_schema


class pg_connection(object):
    """Connect to the PostgreSQL database server"""

    conn = None
    cur = None

    def __init__(self):
        self.openConnection()
        self.setSearchPathToImportSchema()

    def openConnection(self):
        logger = get_run_logger()
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
        logger = get_run_logger()
        if self.conn is not None:
            self.conn.commit()
            logger.info("Transaction commited.")

    def close_connection(self):
        logger = get_run_logger()
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
        logger = get_run_logger()
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
