import os

import sqlalchemy as sa
from shared_tasks.config import db_schema
from sqlalchemy.dialects import postgresql


def quote_identifier(identifier: str) -> str:
    """Protège un identifiant PostgreSQL, notamment les noms de schémas."""
    return postgresql.dialect().identifier_preparer.quote_identifier(identifier)


def make_connection_string() -> str:
    """Returns the connection string for the designated database.

    Returns:
        str: connection string for selected database.

    Raises:
        ValueError: with credentials for the selected database are not found in
        environment variables.
    """

    CLIENT = "postgresql"
    HOST = os.getenv("POSTGRES_HOST")
    PORT = os.getenv("POSTGRES_PORT", default=5432)
    DBNAME = os.getenv("POSTGRES_DB")
    USER = os.getenv("POSTGRES_USER")
    PWD = os.getenv("POSTGRES_PASS")

    return f"{CLIENT}://{USER}:{PWD}@{HOST}:{PORT}/{DBNAME}"


def create_engine(schema: str | None = None, **kwargs) -> sa.engine.Engine:
    """Crée un moteur PostgreSQL dans le schéma demandé ou dans IMPORT_SCHEMA."""
    connection_string = make_connection_string()
    target_schema = quote_identifier(db_schema() if schema is None else schema)
    engine = sa.create_engine(connection_string, **kwargs)

    @sa.event.listens_for(engine, "connect")
    def configure_schema(connection, connection_record):
        """Initialise le schéma et conserve les extensions de public accessibles."""
        previous_autocommit = connection.autocommit
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {target_schema}")
                cursor.execute(f"SET search_path TO {target_schema}, public")
        finally:
            connection.autocommit = previous_autocommit

    return engine
