import os
from prefect import flow, task
from sqlalchemy import DDL

from urbaflow.flows.fppm.import_fppm import list_files_at_path
from urbaflow.shared_tasks.config import TEMP_DIR
from urbaflow.shared_tasks.db_engine import create_engine
from urbaflow.shared_tasks.db_sql_utils import run_sql_script
from urbaflow.shared_tasks.etl_file_utils import download_and_unzip, split_csv_file
from urbaflow.shared_tasks.logging_config import get_logger


# https://www.data.gouv.fr/fr/datasets/referentiel-national-des-batiments/

# URL stable département 92
# https://www.data.gouv.fr/fr/datasets/r/bb1de0fc-9db4-43c7-8308-e23a6459470d

# %%
RNB_URL = "https://www.data.gouv.fr/fr/datasets/r/bb1de0fc-9db4-43c7-8308-e23a6459470d"


@task
def create_temporary_table():
    """
    Create a temporary table in the database to hold raw data.
    """
    e = create_engine()
    logger = get_logger()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                DROP TABLE IF EXISTS rnb_temp_table;
                CREATE TABLE IF NOT EXISTS rnb_temp_table (
                    rnb_id BIGINT,
                    point_ewkt TEXT,
                    shape_ewkt TEXT,
                    status TEXT,
                    ext_ids TEXT,
                    addresses TEXT
                );
                """
            )
        )
        logger.info("Created temporary table rnb_temp_table.")


@task
def load_chunk_into_temporary_table(chunk_file: str):
    """
    Load a single CSV chunk into the temporary table.
    """
    e = create_engine()

    with e.begin() as conn:
        with open(chunk_file, "r", encoding="utf-8") as f:
            dbapi_cursor = conn.connection.cursor()
            dbapi_cursor.copy_expert(
                """
                COPY rnb_temp_table (rnb_id, point_ewkt, shape_ewkt, status, ext_ids, addresses)
                FROM STDIN CSV HEADER QUOTE '\"' DELIMITER ',';
            """,
                f,
            )


@task
def create_final_table():
    """
    Create the final table that will hold the transformed data.
    """
    e = create_engine()
    logger = get_logger()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                DROP TABLE IF EXISTS table_finale;
                CREATE TABLE table_finale (
                    rnb_id BIGINT,
                    point_geom GEOMETRY(POINT, 4326),
                    shape_geom GEOMETRY(MULTIPOLYGON, 4326),
                    status TEXT,
                    ext_ids jsonb,
                    addresses jsonb
                )
                """
            )
        )
        logger.info("Created final table table_finale.")


@task
def transform_and_insert_data():
    """
    Transform the data (EWKT to geometry, text to JSONB) and insert into the final table.
    """
    e = create_engine()
    logger = get_logger()
    with e.begin() as conn:
        sql_query = """
            INSERT INTO table_finale (rnb_id, point_geom, shape_geom, status, ext_ids, addresses)
            SELECT rnb_id,
                ST_GeomFromEWKT(point_ewkt),
                ST_GeomFromEWKT(shape_ewkt),
                status,
                ext_ids::jsonb,
                addresses::jsonb
            FROM rnb_temp_table;
        """
        run_sql_script(sql=sql_query, connection=conn)
        logger.info("Inserted transformed data into table_finale.")


@task
def cleanup_chunk_files(chunk_files: list[str]):
    """
    Remove the chunk files after successful import if desired.
    """
    for cf in chunk_files:
        os.remove(cf)


@flow(name="Inport RNB")
def import_rnb_flow():
    LINES_PER_CHUNK = 100000
    download_path = TEMP_DIR / "rnb"
    download_and_unzip(url=RNB_URL, extract_to_path=download_path)
    create_temporary_table()
    rnb_files = list_files_at_path(download_path, r"^RNB_\d{2,3}\.csv$")
    for rnb_file in rnb_files:
        chunk_files = split_csv_file(
            rnb_file, TEMP_DIR / "rnb_splitted", LINES_PER_CHUNK
        )
        load_results = [  # noqa: F841
            load_chunk_into_temporary_table.submit(chunk) for chunk in chunk_files
        ]

    create_final_table()
    transform_and_insert_data()
    # cleanup_chunk_files(chunk_files)
