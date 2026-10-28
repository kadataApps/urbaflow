"""
Utilitaires communs aux flux d'import de données au format (Geo)Parquet via DuckDB.

Ce module centralise :
- la conversion des noms de colonnes camelCase (convention Sirene/INSEE et de
  nombreux jeux de données data.gouv.fr) vers snake_case (convention PostgreSQL
  utilisée dans le projet),
- la conversion des types de colonnes DuckDB vers des types PostgreSQL
  équivalents, utile pour générer dynamiquement des tables à partir du schéma
  d'un fichier Parquet,
- la lecture du schéma d'un fichier (Geo)Parquet via DuckDB.

Il est utilisé par les flux GeoSirene et Sirene Etablissement (INSEE), et a
vocation à être réutilisé par tout futur flux basé sur des fichiers
(Geo)Parquet.
"""

import re
from pathlib import Path

import duckdb
from prefect import task
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)

# Mapping des types de colonnes DuckDB vers les types PostgreSQL
DUCKDB_TO_POSTGRES_TYPES = {
    "VARCHAR": "text",
    "BIGINT": "bigint",
    "INTEGER": "integer",
    "DOUBLE": "double precision",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "TIMESTAMP": "timestamp",
}


def camel_to_snake_case(name: str) -> str:
    """
    Convertit un nom de colonne camelCase (convention Sirene/INSEE) en snake_case
    (convention PostgreSQL utilisée dans le projet).
    """
    step1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    step2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step1)
    return step2.lower()


def duckdb_type_to_postgres_type(duckdb_type: str) -> str:
    """
    Convertit un type de colonne DuckDB en type PostgreSQL équivalent. Retombe sur
    `text` si le type n'est pas explicitement pris en charge.
    """
    return DUCKDB_TO_POSTGRES_TYPES.get(duckdb_type.upper(), "text")


@task
def get_parquet_schema(parquet_path: Path) -> list[tuple[str, str]]:
    """
    Récupère le schéma (nom de colonne, type DuckDB) d'un fichier (Geo)Parquet,
    afin de pouvoir générer dynamiquement la table PostgreSQL correspondante.
    """
    con = duckdb.connect()
    rows = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{parquet_path.as_posix()}') LIMIT 0"
    ).fetchall()
    columns = [(row[0], row[1]) for row in rows]
    logger.info("Schéma du fichier %s : %d colonnes", parquet_path.name, len(columns))
    return columns
