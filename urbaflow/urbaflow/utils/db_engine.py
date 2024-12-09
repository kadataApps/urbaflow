import os
import sqlalchemy as sa


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


def create_engine(**kwargs) -> sa.engine.Engine:
    """Returns sqlalchemy engine for designated database.


    Returns:
        sa.engine.Engine: sqlalchemy engine for selected database.
    """
    connection_string = make_connection_string()

    engine = sa.create_engine(connection_string, **kwargs)

    return engine
