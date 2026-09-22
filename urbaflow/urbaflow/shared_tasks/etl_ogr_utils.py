import os
import subprocess

from shared_tasks.config import db_config, db_schema
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)


def import_vector_layer(
    file: str,
    table: str,
    schema: str,
    layer: str | None = None,
    source_srs: str | None = None,
    destination_srs: str = "EPSG:2154",
    replace: bool = False,
    force_2d: bool = False,
    spatial_extent: tuple[float, float, float, float] | None = None,
    where: str | None = None,
) -> None:
    """
    Importe une couche vectorielle (GeoPackage, shapefile, ...) dans PostGIS
    via ogr2ogr.

    Contrairement à `import_shapefile`, cette fonction lève une exception si
    ogr2ogr échoue, et ne transmet jamais le mot de passe dans la ligne de commande.

    Args:
        file: chemin du fichier source.
        table: nom de la table cible.
        schema: schéma cible.
        layer: nom de la couche à importer (obligatoire pour les fichiers multicouches).
        source_srs: système de coordonnées source. Si None, le système déclaré
            dans le fichier source est utilisé.
        destination_srs: système de coordonnées cible.
        replace: si True, la table cible est recréée, sinon les données sont ajoutées.
        force_2d: si True, les géométries 3D sont aplaties en 2D.
        spatial_extent: emprise (xmin, ymin, xmax, ymax) exprimée dans le SRS source,
            permettant de ne lire qu'une partie de la couche.
        where: filtre attributaire SQL appliqué à la couche source.

    Raises:
        RuntimeError: si la commande ogr2ogr retourne un code d'erreur.
    """
    params = db_config()
    connection_string = (
        f"PG:host={params['host']} port={params['port']} "
        f"user={params['user']} dbname={params['database']}"
    )

    command = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        connection_string,
        str(file),
        "-nln",
        f"{schema}.{table}",
        "-lco",
        "GEOMETRY_NAME=geom",
        "-lco",
        "PRECISION=NO",
        "-lco",
        "SPATIAL_INDEX=NONE",
        "-t_srs",
        destination_srs,
        "-nlt",
        "PROMOTE_TO_MULTI",
        "--config",
        "PG_USE_COPY",
        "YES",
    ]
    if source_srs:
        command += ["-s_srs", source_srs]
    command += ["-overwrite"] if replace else ["-append", "-update"]
    if force_2d:
        command += ["-dim", "XY"]
    if spatial_extent:
        command += ["-spat", *[str(coordinate) for coordinate in spatial_extent]]
    if where:
        command += ["-where", where]
    if layer:
        command += [layer]

    environment = os.environ.copy()
    if params["password"]:
        environment["PGPASSWORD"] = params["password"]

    logger.info("Exécution de : %s", " ".join(command))
    result = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False
    )
    if result.stdout.strip():
        logger.info(result.stdout.strip())
    if result.returncode != 0:
        logger.error(result.stderr.strip())
        raise RuntimeError(
            f"Échec de l'import ogr2ogr de {file} "
            f"(couche {layer}) vers {schema}.{table}"
        )
    if result.stderr.strip():
        logger.warning(result.stderr.strip())


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
        f"-lco GEOMETRY_NAME=geom -lco PRECISION=NO "
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
