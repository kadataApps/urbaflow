import os
from prefect import get_run_logger
from shared_tasks.config import db_config, db_schema


def import_shapefile(
    file: str,
    table: str,
    schema: str,
    destination_srs: str = "EPSG:2154",
    source_srs: str = "EPSG:4326",
):
    logger = get_run_logger()
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
        f'"{params["file"]}" -nln {params["schema"]}.{params["table"]} '
        f'-lco GEOMETRY_NAME=geom '
        f'-append -update -skipfailures -s_srs "{source_srs}" -t_srs "{destination_srs}" -nlt "PROMOTE_TO_MULTI"'
    )

    logger.info(command)
    try:
        os.system(command)
    except OSError as e:
        logger.error(e)


def import_geojson(file: str, table: str):
    logger = get_run_logger()
    params = db_config()
    schema = db_schema()

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
        f'"{file}" -nln {schema}.{table} -append -update -skipfailures -a_srs "EPSG:4326" -nlt "PROMOTE_TO_MULTI"'
    )
    logger.info(command)
    try:
        os.system(command)
    except OSError as e:
        logger.error(e)
