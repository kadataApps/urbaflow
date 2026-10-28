from pathlib import Path

import duckdb
import pandas as pd
from prefect import flow, task
from shared_tasks.db_engine import create_engine
from shared_tasks.duckdb_utils import (
    camel_to_snake_case,
    duckdb_type_to_postgres_type,
    get_parquet_schema,
)
from shared_tasks.etl_file_utils import fetch_or_find_file
from shared_tasks.etl_gpd_utils import load
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

# Stock des établissements Sirene (GeoParquet)
# URL stable data.gouv.fr :
# https://www.data.gouv.fr/api/1/datasets/r/a29c1297-1f92-4e2a-8f6b-8c902ce96c5f
#
# Ce fichier contient les données descriptives (non géolocalisées) de tous les
# établissements du répertoire Sirene (INSEE). Il est volumineux (plusieurs Go), il
# est donc conseillé de filtrer l'import par communes ou par département.

logger = get_logger(__name__)

SIRENE_ETABLISSEMENT_PARQUET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/a29c1297-1f92-4e2a-8f6b-8c902ce96c5f"
)


@task
def fetch_sirene_etablissement_parquet(dirname: Path | None = None) -> Path:
    """
    Télécharge le fichier GeoParquet du stock des établissements Sirene s'il n'est
    pas fourni localement.

    Ce fichier pèse plusieurs Go, le téléchargement peut donc prendre du temps.
    """
    return fetch_or_find_file(
        url=SIRENE_ETABLISSEMENT_PARQUET_URL,
        cache_subdir="sirene_etablissement",
        cache_filename="sirene_etablissement.parquet",
        dirname=dirname,
    )


@task
def create_sirene_etablissement_table(
    columns: list[tuple[str, str]],
    db_schema: str = "public",
    table_name: str = "sirene_etablissement",
    recreate: bool = True,
):
    """
    Crée la table sirene_etablissement dans PostgreSQL à partir du schéma du
    fichier GeoParquet (colonnes converties en snake_case).
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {q(db_schema)}.{q(table_name)}"))
            logger.info(
                "Suppression de la table %s.%s si elle existe", db_schema, table_name
            )

        column_defs = []
        for name, duckdb_type in columns:
            snake_name = camel_to_snake_case(name)
            pg_type = duckdb_type_to_postgres_type(duckdb_type)
            if snake_name == "siret":
                column_defs.append(f"{q(snake_name)} {pg_type} PRIMARY KEY")
            else:
                column_defs.append(f"{q(snake_name)} {pg_type}")
        column_defs.append(f"{q('urbaflow_inserted_at')} timestamp")

        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {q(db_schema)}.{q(table_name)} (
                    {", ".join(column_defs)}
                )
                """
            )
        )
        conn.execute(
            DDL(
                f"""
                CREATE INDEX IF NOT EXISTS
                    {q(f"idx_{table_name}_code_commune_etablissement")}
                ON {q(db_schema)}.{q(table_name)} (code_commune_etablissement)
                """
            )
        )
        logger.info(
            "Table %s.%s créée si elle n'existait pas auparavant",
            db_schema,
            table_name,
        )


@task
def get_communes_codes_from_geosirene(
    db_schema: str = "public",
    geosirene_table_name: str = "geosirene_etablissement",
) -> list[str]:
    """
    Récupère la liste des codes commune déjà présents dans la table
    geosirene_etablissement, afin de filtrer l'import (volumineux) de
    sirene_etablissement sur ce périmètre.
    """
    e = create_engine()
    with e.connect() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        result = conn.execute(
            text(
                f"""
                SELECT DISTINCT plg_code_commune
                FROM {q(db_schema)}.{q(geosirene_table_name)}
                WHERE plg_code_commune IS NOT NULL
                """
            )
        )
        communes = sorted({row[0] for row in result.fetchall()})
    logger.info(
        "%d codes commune trouvés dans %s.%s pour filtrer l'import Sirene",
        len(communes),
        db_schema,
        geosirene_table_name,
    )
    return communes


@task
def extract_and_load_sirene_etablissement(
    parquet_path: Path,
    columns: list[tuple[str, str]],
    communes: list[str] | None = None,
    department: str | None = None,
    db_schema: str = "public",
    table_name: str = "sirene_etablissement",
    recreate: bool = False,
    chunk_size: int = 200_000,
):
    """
    Extrait les établissements Sirene (filtrés par communes ou par département si
    spécifié) et les insère dans la table PostgreSQL, par lots afin de maîtriser la
    consommation mémoire.
    """
    select_cols = ", ".join(
        f'"{name}" AS {camel_to_snake_case(name)}' for name, _ in columns
    )

    params = None
    if communes:
        where_clause = 'WHERE "codeCommuneEtablissement" = ANY(?)'
        params = [communes]
        logger.info(
            "Extraction des établissements Sirene filtrée sur %d communes",
            len(communes),
        )
    elif department:
        dep_str = str(department).strip()
        where_clause = f"WHERE \"codeCommuneEtablissement\" LIKE '{dep_str}%'"
        logger.info(
            "Extraction des établissements Sirene pour le département %s", dep_str
        )
    else:
        where_clause = ""
        logger.warning(
            "Aucun filtre (communes ou département) fourni : extraction de la "
            "totalité des établissements Sirene, cet import peut être très long."
        )

    query = f"""
        SELECT {select_cols}
        FROM read_parquet('{parquet_path.as_posix()}')
        {where_clause}
    """

    e = create_engine()

    if not recreate and (communes or department):
        with e.begin() as conn:
            q = conn.engine.dialect.identifier_preparer.quote
            if communes:
                logger.info(
                    "Suppression des anciens établissements des communes filtrées "
                    "dans %s.%s",
                    db_schema,
                    table_name,
                )
                conn.execute(
                    text(
                        f"DELETE FROM {q(db_schema)}.{q(table_name)} "
                        "WHERE code_commune_etablissement = ANY(:communes)"
                    ),
                    {"communes": communes},
                )
            elif department:
                dep_str = str(department).strip()
                logger.info(
                    "Suppression des anciens établissements du département %s "
                    "dans %s.%s",
                    dep_str,
                    db_schema,
                    table_name,
                )
                conn.execute(
                    text(
                        f"DELETE FROM {q(db_schema)}.{q(table_name)} "
                        "WHERE code_commune_etablissement LIKE :dep_pattern"
                    ),
                    {"dep_pattern": f"{dep_str}%"},
                )

    con = duckdb.connect()
    result = con.execute(query, params) if params else con.execute(query)

    # `vectors_per_chunk` est exprimé en nombre de vecteurs internes DuckDB
    # (2048 lignes par défaut). On l'ajuste pour approcher chunk_size lignes.
    vectors_per_chunk = max(1, chunk_size // 2048)

    total_rows = 0
    while True:
        df = result.fetch_df_chunk(vectors_per_chunk)
        if df.empty:
            break
        df["siret"] = df["siret"].astype(str)
        df["urbaflow_inserted_at"] = pd.Timestamp.now()

        with e.begin() as conn:
            load(
                df,
                connection=conn,
                table_name=table_name,
                schema=db_schema,
                how="append",
                logger=logger,
            )
        total_rows += len(df)
        logger.info("%d établissements Sirene insérés au total", total_rows)

    if total_rows == 0:
        logger.warning("Aucun établissement Sirene trouvé avec la requête fournie")


@task
def create_geosirene_etablissement_detail_table(
    db_schema: str = "public",
    detail_table_name: str = "geosirene_etablissement_detail",
    geosirene_table_name: str = "geosirene_etablissement",
    sirene_table_name: str = "sirene_etablissement",
    recreate: bool = True,
):
    """
    Crée la table geosirene_etablissement_detail, résultat de la jointure entre
    geosirene_etablissement (établissements géolocalisés) et sirene_etablissement
    (données descriptives Sirene). Seuls les établissements présents dans
    geosirene_etablissement ET dans sirene_etablissement sont conservés : les
    établissements de sirene_etablissement sans correspondance dans
    geosirene_etablissement ne sont pas repris.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote

        table_exists = conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = :schema AND table_name = :table_name
                )
                """
            ),
            {"schema": db_schema, "table_name": detail_table_name},
        ).scalar()

        if table_exists and not recreate:
            logger.info(
                "Table %s.%s déjà existante, création ignorée (recreate=False)",
                db_schema,
                detail_table_name,
            )
            return

        sirene_columns = conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = :table_name
                ORDER BY ordinal_position
                """
            ),
            {"schema": db_schema, "table_name": sirene_table_name},
        ).fetchall()
        sirene_column_names = [row[0] for row in sirene_columns if row[0] != "siret"]

        if not sirene_column_names:
            raise ValueError(
                f"La table {db_schema}.{sirene_table_name} est introuvable ou vide "
                "de colonnes. Importez d'abord les données Sirene Etablissement."
            )

        sirene_select = ", ".join(
            f"s.{q(name)} AS {q(f'sirene_{name}')}" for name in sirene_column_names
        )

        conn.execute(DDL(f"DROP TABLE IF EXISTS {q(db_schema)}.{q(detail_table_name)}"))
        logger.info(
            "Création de la table %s.%s par jointure entre %s et %s",
            db_schema,
            detail_table_name,
            geosirene_table_name,
            sirene_table_name,
        )
        conn.execute(
            DDL(
                f"""
                CREATE TABLE {q(db_schema)}.{q(detail_table_name)} AS
                SELECT g.*, {sirene_select}
                FROM {q(db_schema)}.{q(geosirene_table_name)} AS g
                INNER JOIN {q(db_schema)}.{q(sirene_table_name)} AS s
                    ON g.siret = s.siret
                """
            )
        )
        conn.execute(
            text(
                f"""
                ALTER TABLE {q(db_schema)}.{q(detail_table_name)}
                ADD CONSTRAINT {q(f"pk_{detail_table_name}")} PRIMARY KEY (siret);
                """
            )
        )
        conn.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS {q(f"sidx_{detail_table_name}_geom")}
                ON {q(db_schema)}.{q(detail_table_name)} USING GIST (geom);
                """
            )
        )
        count = conn.execute(
            text(f"SELECT COUNT(*) FROM {q(db_schema)}.{q(detail_table_name)}")
        ).scalar()
        logger.info(
            "Table %s.%s créée avec succès (%d lignes)",
            db_schema,
            detail_table_name,
            count,
        )


@flow
def import_sirene_etablissement_data(
    department: str | None = None,
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "sirene_etablissement",
    geosirene_table_name: str = "geosirene_etablissement",
    filter_by_geosirene_communes: bool = True,
    recreate: bool = True,
    chunk_size: int = 200_000,
):
    """
    Flow d'importation des données descriptives des établissements Sirene
    (format GeoParquet).

    Par défaut (`filter_by_geosirene_communes=True` et `department=None`), l'import
    est filtré sur les communes déjà présentes dans la table
    geosirene_etablissement, afin de limiter le volume de données traitées.
    """
    logger.info("Début de l'import des établissements Sirene")
    parquet_path = fetch_sirene_etablissement_parquet(dirname=dirname)
    columns = get_parquet_schema(parquet_path)
    create_sirene_etablissement_table(
        columns, db_schema=db_schema, table_name=table_name, recreate=recreate
    )

    communes = None
    if filter_by_geosirene_communes and not department:
        communes = get_communes_codes_from_geosirene(
            db_schema=db_schema, geosirene_table_name=geosirene_table_name
        )

    extract_and_load_sirene_etablissement(
        parquet_path=parquet_path,
        columns=columns,
        communes=communes,
        department=department,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
        chunk_size=chunk_size,
    )
    logger.info("Import des établissements Sirene terminé avec succès !")


@flow
def create_geosirene_etablissement_detail(
    db_schema: str = "public",
    detail_table_name: str = "geosirene_etablissement_detail",
    geosirene_table_name: str = "geosirene_etablissement",
    sirene_table_name: str = "sirene_etablissement",
    recreate: bool = True,
):
    """
    Flow de création de la table geosirene_etablissement_detail, jointure entre
    geosirene_etablissement et sirene_etablissement.
    """
    logger.info("Début de la création de la table geosirene_etablissement_detail")
    create_geosirene_etablissement_detail_table(
        db_schema=db_schema,
        detail_table_name=detail_table_name,
        geosirene_table_name=geosirene_table_name,
        sirene_table_name=sirene_table_name,
        recreate=recreate,
    )
    logger.info("Création de la table geosirene_etablissement_detail terminée !")
