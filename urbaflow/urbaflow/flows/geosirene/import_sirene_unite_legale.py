"""Import du stock Parquet des unités légales liées aux établissements importés."""

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
from sqlalchemy import text

logger = get_logger(__name__)

SIRENE_UNITE_LEGALE_PARQUET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/350182c9-148a-46e0-8389-76c2ec1374a3"
)


@task
def fetch_sirene_unite_legale_parquet(dirname: Path | None = None) -> Path:
    """Télécharge le stock des unités légales ou utilise un parquet local."""
    return fetch_or_find_file(
        url=SIRENE_UNITE_LEGALE_PARQUET_URL,
        cache_subdir="sirene_unite_legale",
        cache_filename="sirene_unite_legale.parquet",
        dirname=dirname,
    )


@task
def load_sirene_unite_legale(
    parquet_path: Path,
    columns: list[tuple[str, str]],
    db_schema: str = "public",
    table_name: str = "sirene_unite_legale",
    sirene_table_name: str = "sirene_etablissement",
    recreate: bool = True,
    chunk_size: int = 200_000,
) -> int:
    """Charge toutes les colonnes des unités légales du périmètre, par lots."""
    engine = create_engine()
    with engine.begin() as connection, duckdb.connect() as source:
        quote = connection.engine.dialect.identifier_preparer.quote
        target = f"{quote(db_schema)}.{quote(table_name)}"
        establishments = f"{quote(db_schema)}.{quote(sirene_table_name)}"
        sirens = pd.read_sql_query(
            text(
                f"SELECT DISTINCT siren FROM {establishments} WHERE siren IS NOT NULL"
            ),
            connection,
        )
        if sirens.empty:
            raise ValueError(
                "Aucun SIREN à enrichir. Importez d'abord les établissements Sirene."
            )
        source.register("selected_sirens", sirens)
        select_columns = ", ".join(
            f'u."{name}" AS "{camel_to_snake_case(name)}"' for name, _ in columns
        )
        result = source.execute(
            f"""
            SELECT {select_columns}
            FROM read_parquet(?) AS u
            SEMI JOIN selected_sirens AS selected ON u.siren = selected.siren
            """,
            [str(parquet_path)],
        )
        column_definitions = ", ".join(
            f"{quote(camel_to_snake_case(name))} "
            f"{duckdb_type_to_postgres_type(column_type)}"
            + (" PRIMARY KEY" if name == "siren" else "")
            for name, column_type in columns
        )
        if recreate:
            connection.execute(text(f"DROP TABLE IF EXISTS {target}"))
        connection.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {target} "
                f"({column_definitions}, urbaflow_inserted_at timestamp)"
            )
        )
        if not recreate:
            connection.execute(
                text(
                    f"DELETE FROM {target} WHERE siren IN "
                    f"(SELECT siren FROM {establishments})"
                )
            )
        total_rows = 0
        while True:
            frame = result.fetch_df_chunk(max(1, chunk_size // 2048))
            if frame.empty:
                break
            frame["urbaflow_inserted_at"] = pd.Timestamp.now()
            load(
                frame,
                connection=connection,
                table_name=table_name,
                schema=db_schema,
                how="append",
                logger=logger,
            )
            total_rows += len(frame)
            logger.info("%d unités légales insérées au total", total_rows)
        if total_rows == 0:
            raise ValueError("Aucune unité légale trouvée pour les SIREN importés.")
        if total_rows < len(sirens):
            logger.warning(
                "%d SIREN sans correspondance dans le stock des unités légales",
                len(sirens) - total_rows,
            )
    return total_rows


@flow
def import_sirene_unite_legale_data(
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "sirene_unite_legale",
    sirene_table_name: str = "sirene_etablissement",
    recreate: bool = True,
):
    """Importe les unités légales correspondant aux établissements déjà chargés."""
    parquet_path = fetch_sirene_unite_legale_parquet(dirname=dirname)
    columns = get_parquet_schema(parquet_path)
    load_sirene_unite_legale(
        parquet_path=parquet_path,
        columns=columns,
        db_schema=db_schema,
        table_name=table_name,
        sirene_table_name=sirene_table_name,
        recreate=recreate,
    )
    logger.info("Import des unités légales Sirene terminé")
