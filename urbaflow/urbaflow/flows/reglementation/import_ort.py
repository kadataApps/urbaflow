from prefect import flow
from sqlalchemy import DDL
import pandas as pd
from shared_tasks.db_engine import create_engine
from shared_tasks.logging_config import get_logger


URL_ORT_CSV = (
    "https://www.data.gouv.fr/fr/datasets/r/17a6bc80-297a-4dc2-b98c-3edc12161bc0"
)


def create_table_ort(schema="public", table_name="ort"):
    """
    Creates the ort table in the database if it does not exist.
    """
    logger = get_logger()
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.{table_name} (
                        commune TEXT,
                        epci TEXT,
                        departement TEXT,
                        region TEXT,
                        code_commune TEXT NOT NULL PRIMARY KEY,
                        statut_commune TEXT,
                        signe TEXT,
                        date_signature DATE,
                        date_signature_envisagee DATE,
                        duree INTEGER,
                        date_fin_estimee DATE,
                        remarques TEXT,
                        avancement TEXT,
                        acv BOOLEAN,
                        pvd BOOLEAN,
                        longitude NUMERIC,
                        latitude NUMERIC,
                        derniere_actualisation DATE,
                        actualise_par TEXT
                )
                """
            )
        )
        logger.info(f"Table {schema}.{table_name} created successfully")


def drop_table_ort(schema="public", table_name="ort"):
    logger = get_logger()
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                f"""
                DROP TABLE IF EXISTS {schema}.{table_name}
                """
            )
        )
        logger.info(f"Table {schema}.{table_name} dropped successfully")


def read_ort_csv():
    """
    Reads the CSV file from the URL and returns a DataFrame.
    Renames the columns to match the database schema.
    Converts the 'pvd' and 'acv' columns to boolean.
    Converts the 'date_signature', 'date_signature_envisagee', 'date_fin_estimee', and 'derniere_actualisation' columns to datetime.
    Converts the 'longitude' and 'latitude' columns to float.
    Remove lines with missing values in the 'code_commune' column.
    Ensure code_commune is unique.
    """
    logger = get_logger()
    df = pd.read_csv(URL_ORT_CSV, sep=",", encoding="utf-8")
    df.columns = [
        "commune",
        "epci",
        "departement",
        "region",
        "code_commune",
        "statut_commune",
        "signe",
        "date_signature",
        "date_signature_envisagee",
        "duree",
        "date_fin_estimee",
        "remarques",
        "avancement",
        "acv",
        "pvd",
        "longitude",
        "latitude",
        "derniere_actualisation",
        "actualise_par",
    ]
    df = df.dropna(subset=["code_commune"])
    df = df.reset_index(drop=True)

    df["acv"] = df["acv"].astype(bool)
    df["pvd"] = df["pvd"].astype(bool)
    df["date_signature"] = pd.to_datetime(df["date_signature"], errors="coerce")
    df["date_signature_envisagee"] = pd.to_datetime(
        df["date_signature_envisagee"], errors="coerce"
    )
    df["date_fin_estimee"] = pd.to_datetime(df["date_fin_estimee"], errors="coerce")
    df["derniere_actualisation"] = pd.to_datetime(
        df["derniere_actualisation"], errors="coerce"
    )
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")

    # Ensure 'code_commune' is unique
    # If there are duplicates, tell which ones are dropped
    duplicates = df[df.duplicated(subset=["code_commune"], keep=False)]
    if not duplicates.empty:
        logger.warning(f"Found {len(duplicates)} duplicates in 'code_commune':")
        for code in duplicates["code_commune"].unique():
            logger.warning(f"Duplicate code_commune: {code}")
        # Drop duplicates based on 'code_commune', keeping the first occurrence
        df = df.drop_duplicates(subset=["code_commune"])
        logger.info(f"Kept {len(df)} unique rows after removing duplicates")

    logger.info(f"Final DataFrame shape: {df.shape}")
    return df


def insert_ort_data(df, schema="public", table_name="ort"):
    """
    Inserts the DataFrame into the database table.
    """
    logger = get_logger()
    e = create_engine()
    with e.begin() as conn:
        df.to_sql(table_name, con=conn, schema=schema, if_exists="append", index=False)
        logger.info(f"Inserted {len(df)} rows into {schema}.{table_name}")


@flow
def import_ort(schema="public", table_name="ort"):
    """
    Import ORT (Opérations de Revitalisation de Territoire) data
    """
    logger = get_logger()
    logger.info("Starting ORT import flow")

    drop_table_ort(schema=schema, table_name=table_name)
    create_table_ort(schema=schema, table_name=table_name)
    df = read_ort_csv()
    insert_ort_data(df, schema=schema, table_name=table_name)

    logger.info("ORT import flow completed successfully")
