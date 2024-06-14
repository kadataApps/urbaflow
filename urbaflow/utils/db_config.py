import os
import sqlalchemy as sa

# from dotenv import load_dotenv
# from config import ROOT_DIRECTORY

# load_dotenv(ROOT_DIRECTORY / ".env")

db_env = {
    "local": {
        "client": "postgresql",
        "host": "POSTGRES_HOST",
        "port": "POSTGRES_PORT",
        "sid": "POSTGRES_DB",
        "usr": "POSTGRES_USER",
        "pwd": "POSTGRES_PASS",
    },
   
}

def make_connection_string(db: str) -> str:
    """Returns the connection string for the designated database.

    Args:
        db (str): Database name. Possible values :
        'ocan', 'fmc', 'monitorenv_remote', 'monistorfish_local'

    Returns:
        str: connection string for selected database.

    Raises:
        ValueError: with credentials for the selected database are not found in
        environment variables.
    """

    try:
        CLIENT = db_env[db]["client"]
        HOST = os.environ[db_env[db]["host"]]
        PORT = os.environ[db_env[db]["port"]]
        SID = os.environ[db_env[db]["sid"]]
        USER = os.environ[db_env[db]["usr"]]
        PWD = os.environ[db_env[db]["pwd"]]
    except KeyError as e:
        raise KeyError(
            "Database connection credentials not found in environment: ",
            e.args,
        )

    return f"{CLIENT}://{USER}:{PWD}@{HOST}:{PORT}/{SID}"


def create_engine(db: str, **kwargs) -> sa.engine.Engine:
    """Returns sqlalchemy engine for designated database.

    Args:
        db (str): Database name. Possible values :
            'local'

    Returns:
        sa.engine.Engine: sqlalchemy engine for selected database.
    """
    connection_string = make_connection_string(db)

    engine = sa.create_engine(connection_string, **kwargs)

    return engine
