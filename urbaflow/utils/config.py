#!/usr/bin/python
import os
from pathlib import Path
from configparser import ConfigParser

defaultConfig = os.path.join(Path(__file__).resolve().parent.parent, "config.ini")

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent.parent
LIBRARY_LOCATION = ROOT_DIRECTORY / Path("src")


def config(filename=defaultConfig, section="postgresql"):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    parameters = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            parameters[param[0]] = param[1]
    else:
        raise Exception(
            "Section {0} not found in the {1} file".format(section, filename)
        )

    return parameters


def db_config():
    return {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT", default=5432),
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASS"),
    }


def db_schema():
    return {
        "schema": os.getenv("IMPORT_SCHEMA", default="public"),
    }


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
