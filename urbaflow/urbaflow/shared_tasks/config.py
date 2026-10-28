import os
from pathlib import Path

APP_DIR = Path(__file__).parent.parent.resolve()

TEMP_DIR = APP_DIR / "../temp"

QUERIES_DIR = APP_DIR / "queries"


def db_config():
    return {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT", default=5432),
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASS"),
    }


def db_schema() -> str:
    """Renvoie le schéma de destination des imports et des résultats consolidés."""
    return os.getenv("IMPORT_SCHEMA", default="public")


def majic_schema() -> str:
    """Renvoie un schéma de travail MAJIC distinct du schéma de destination."""
    schema = os.getenv("MAJIC_SCHEMA", default="majic")
    if (
        not schema
        or schema == db_schema()
        or schema in {"public", "information_schema"}
        or schema.startswith("pg_")
    ):
        raise ValueError(
            "MAJIC_SCHEMA doit désigner un schéma de travail non système, "
            "différent de public et d'IMPORT_SCHEMA."
        )
    return schema


def majic_config():
    MAJIC_FILE_NAMES = {
        "bati": "BATI",
        "nbati": "NBAT",
        "pdll": "PDLL",
        "lotlocal": "LLOC",
        "prop": "PROP",
        "max_insert_rows": "50000",
    }
    return MAJIC_FILE_NAMES
