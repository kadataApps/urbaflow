#!/usr/bin/python
import os


def db_config():
    return {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT", default=5432),
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASS"),
    }


def db_schema() -> str:
    return os.getenv("IMPORT_SCHEMA", default="public")


def majic_config():
    return {
        "bati": "BATI",
        "nbati": "NBAT",
        "pdll": "PDLL",
        "fantoir": "FAN",
        "lotlocal": "LLOC",
        "prop": "PROP",
        "max_insert_rows": "50000",
    }