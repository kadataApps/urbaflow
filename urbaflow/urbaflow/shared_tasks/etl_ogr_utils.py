import os

from shared_tasks.config import db_config, db_schema
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)


def import_shapefile(
    file: str,
    table: str,
    schema: str,
    destination_srs: str = "EPSG:2154",
    source_srs: str = "EPSG:4326",
    replace: bool = False,
):
    params = db_config()
    params["table"] = table
    params["file"] = file
    params["schema"] = schema
    method = "-overwrite" if replace else "-append -update"

    password_string = (
        f"PGPASSWORD='{params['password']}'" if params["password"] != "" else ""
    )
    command = (
        f"{password_string} "
        f'ogr2ogr -f "PostgreSQL" '
        f'PG:"host={params["host"]} port={params["port"]} user={params["user"]} '
        f'dbname={params["database"]} " '
        f'"{params["file"]}" -nln {params["schema"]}.{params["table"]} '
        f"-lco GEOMETRY_NAME=geom "
        f"{method} "
        f'-skipfailures -s_srs "{source_srs}" -t_srs "{destination_srs}" '
        f'-nlt "PROMOTE_TO_MULTI"'
    )

    logger.info(command)
    try:
        os.system(command)
    except OSError as e:
        logger.error(e)


def import_geojson(file: str, table: str):
    params = db_config()
    schema = db_schema()

    password_string = (
        f"PGPASSWORD='{params['password']}'" if params["password"] != "" else ""
    )
    command = (
        f"{password_string} "
        f'ogr2ogr -f "PostgreSQL" '
        f'PG:"host={params["host"]} port={params["port"]} user={params["user"]} '
        f'dbname={params["database"]} " '
        f'"{file}" -nln {schema}.{table} -append -update -skipfailures '
        f'-a_srs "EPSG:4326" -nlt "PROMOTE_TO_MULTI"'
    )
    logger.info(command)
    try:
        os.system(command)
    except OSError as e:
        logger.error(e)
