"""Import des contours cadastraux GeoParquet dans PostgreSQL/PostGIS."""

import re
from pathlib import Path

import duckdb
from prefect import flow
from psycopg2.extras import execute_values
from shared_tasks.db_engine import create_engine
from shared_tasks.geopf_utils import Perimeter, resolve_perimeter
from shared_tasks.logging_config import get_logger
from sqlalchemy import text

logger = get_logger(__name__)

DEFAULT_PARQUET_URL = (
    "https://cadastre.data.gouv.fr/data/etalab-cadastre/"
    "2026-09-01/geoparquet/france/cadastre.parquet"
)
OBJECT_TABLES = {
    "communes": "dgfip_commune",
    "sections": "dgfip_section",
    "batiments": "dgfip_batiment",
}
BATCH_SIZE = 5000

# Les noms source et cible ne diffèrent que pour modeConfec.
ATTRIBUTE_COLUMNS = (
    ("millesime", "millesime", "date"),
    ("departement", "departement", "text"),
    ("commune", "commune", "text"),
    ("id", "id", "text"),
    ("section", "section", "text"),
    ("parcelle", "parcelle", "text"),
    ("numero", "numero", "text"),
    ("prefixe", "prefixe", "text"),
    ("code", "code", "text"),
    ("lettre", "lettre", "text"),
    ("nom", "nom", "text"),
    ("created", "created", "date"),
    ("updated", "updated", "date"),
    ("qualite", "qualite", "text"),
    ("modeConfec", "mode_confec", "text"),
    ("echelle", "echelle", "integer"),
    ("ancienne", "ancienne", "text"),
    ("type", "type", "text"),
    ("contenance", "contenance", "bigint"),
    ("geom_srid", "geom_srid", "integer"),
)


def build_perimeter_filter(
    perimeter: Perimeter | None,
) -> tuple[str, list[str]]:
    """Construit un filtre paramétré commun à DuckDB et PostgreSQL."""
    if perimeter is None:
        return "TRUE", []
    if perimeter.insee_codes is not None:
        column = "commune"
        codes = list(perimeter.insee_codes)
        pattern = r"(?:[0-9]{5}|2[AB][0-9]{3})"
    else:
        column = "departement"
        codes = list(perimeter.departments)
        pattern = r"(?:[0-9]{2,3}|2[AB])"
    if not codes or any(re.fullmatch(pattern, code) is None for code in codes):
        raise ValueError(f"Codes de périmètre invalides pour {column} : {codes}")
    placeholders = ", ".join("?" for _ in codes)
    return f"{column} IN ({placeholders})", codes


def open_cadastre_source(
    source: str, perimeter: Perimeter | None
) -> duckdb.DuckDBPyConnection:
    """Ouvre une lecture filtrée du GeoParquet, sans charger le fichier en mémoire."""
    where_clause, codes = build_perimeter_filter(perimeter)
    connection = duckdb.connect()
    try:
        if source.startswith(("https://", "http://")):
            connection.execute("INSTALL httpfs; LOAD httpfs")
        # Le CRS global est erroné : conserver le WKB et utiliser geom_srid par objet.
        connection.execute("SET enable_geoparquet_conversion = false")
        columns = ", ".join(f'"{column[0]}"' for column in ATTRIBUTE_COLUMNS)
        object_placeholders = ", ".join("?" for _ in OBJECT_TABLES)
        connection.execute(
            f"""
            SELECT type_objet, {columns}, geometry
            FROM read_parquet(?)
            WHERE type_objet IN ({object_placeholders}) AND {where_clause}
            """,
            [source, *OBJECT_TABLES, *codes],
        )
    except Exception:
        connection.close()
        raise
    return connection


def load_cadastre(
    source: duckdb.DuckDBPyConnection,
    schema: str,
    perimeter: Perimeter | None,
) -> dict[str, int]:
    """Remplace atomiquement les trois couches sur le seul périmètre demandé."""
    where_clause, codes = build_perimeter_filter(perimeter)
    engine = create_engine()
    counts = dict.fromkeys(OBJECT_TABLES, 0)
    imported_communes: set[str] = set()
    try:
        with engine.begin() as connection:
            quote = connection.dialect.identifier_preparer.quote
            # Sérialiser les imports cadastraux dans un même schéma.
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
                {"lock_name": f"{schema}.dgfip_geoparquet"},
            )
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quote(schema)}"))
            attributes = ", ".join(
                f"{quote(target)} {column_type}"
                for _, target, column_type in ATTRIBUTE_COLUMNS
            )
            columns = ", ".join(
                [quote(column[1]) for column in ATTRIBUTE_COLUMNS] + ["geom"]
            )
            template = (
                "("
                + ", ".join(["%s"] * len(ATTRIBUTE_COLUMNS))
                + ", ST_Multi(ST_Force2D(ST_Transform("
                "ST_SetSRID(ST_GeomFromWKB(%s), %s), 2154))))"
            )
            with connection.connection.cursor() as cursor:
                tables = {
                    object_type: f"{quote(schema)}.{quote(table)}"
                    for object_type, table in OBJECT_TABLES.items()
                }
                for table in tables.values():
                    cursor.execute(
                        f"CREATE TABLE IF NOT EXISTS {table} ("
                        f"fid bigserial PRIMARY KEY, {attributes}, "
                        "geom geometry(MultiPolygon, 2154) NOT NULL)"
                    )
                    cursor.execute(
                        f"DELETE FROM {table} WHERE " + where_clause.replace("?", "%s"),
                        codes,
                    )
                while rows := source.fetchmany(BATCH_SIZE):
                    batches: dict[str, list[tuple]] = {
                        object_type: [] for object_type in OBJECT_TABLES
                    }
                    for object_type, *values in rows:
                        if values[-1] is None or not values[-2]:
                            raise ValueError(
                                f"Géométrie ou geom_srid absent pour {object_type}."
                            )
                        if object_type == "communes":
                            imported_communes.add(values[2])
                        batches[object_type].append((*values, values[-2]))
                    for object_type, batch in batches.items():
                        if not batch:
                            continue
                        execute_values(
                            cursor,
                            f"INSERT INTO {tables[object_type]} ({columns}) VALUES %s",
                            batch,
                            template=template,
                            page_size=BATCH_SIZE,
                        )
                        counts[object_type] += len(batch)
                if not counts["communes"]:
                    raise ValueError(
                        "Aucun contour de commune trouvé sur le périmètre demandé. "
                        "L'import est annulé."
                    )
                if perimeter is not None and perimeter.insee_codes is not None:
                    missing_codes = set(perimeter.insee_codes) - imported_communes
                    if missing_codes:
                        logger.warning(
                            "Communes absentes du GeoParquet : %s",
                            ", ".join(sorted(missing_codes)),
                        )
                for object_type, table in tables.items():
                    table_name = OBJECT_TABLES[object_type]
                    for column, method in (
                        ("geom", "gist"),
                        ("commune", "btree"),
                        ("departement", "btree"),
                    ):
                        index_name = quote(f"{table_name}_{column}_idx")
                        cursor.execute(
                            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} "
                            f"USING {method} ({column})"
                        )
    finally:
        engine.dispose()
    return counts


@flow
def import_dgfip_geoparquet_flow(
    departements: str | None = None,
    epci: str | None = None,
    communes: str | None = None,
    db_schema: str = "public",
    source: str = DEFAULT_PARQUET_URL,
) -> dict[str, int]:
    """Importe les communes, sections et bâtiments, avec un périmètre facultatif."""
    perimeter = None
    if any(option is not None for option in (departements, epci, communes)):
        perimeter = resolve_perimeter(
            departements=departements, epci=epci, communes=communes
        )
    if not source.startswith(("https://", "http://")):
        source = str(Path(source).expanduser().resolve(strict=True))
    logger.info("Début de l'import cadastral GeoParquet depuis %s", source)
    with open_cadastre_source(source, perimeter) as connection:
        counts = load_cadastre(connection, db_schema, perimeter)
    for object_type, count in counts.items():
        logger.info(
            "%s.%s : %d objets importés", db_schema, OBJECT_TABLES[object_type], count
        )
    return counts
