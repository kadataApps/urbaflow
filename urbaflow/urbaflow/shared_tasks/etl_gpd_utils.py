# Inspired by MonitorEnv (c) Vincent Chéry


import logging
from pathlib import Path
from typing import List, Union

import geopandas as gpd
import pandas as pd
from sqlalchemy import DDL, text
from sqlalchemy.engine import Connection

from shared_tasks.processing import prepare_df_for_loading
from shared_tasks.db_utils import (
    get_table,
    delete_rows,
    delete,
)
from shared_tasks.db_sql_utils import psql_insert_copy, read_saved_query


def extract(
    connection: Connection,
    query_filepath: Union[Path, str],
    dtypes: Union[None, dict] = None,
    parse_dates: Union[list, dict, None] = None,
    params=None,
    backend: str = "pandas",
    geom_col: str = "geom",
    crs: Union[int, None] = None,
) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """Run SQL query against the indicated database and return the result as a
    `pandas.DataFrame`.

    Args:
        connection (Connection): SQLAlchemy connection object
        query_filepath (Union[Path, str]): path to .sql file, starting from the saved
            queries folder. example : "ocan/nav_fr_peche.sql"
        dtypes (Union[None, dict], optional): If specified, use {col: dtype, …}, where
            col is a column label and dtype is a numpy.dtype or Python type to cast
            one or more of the DataFrame’s columns to column-specific types.
            Defaults to None.
        parse_dates (Union[list, dict, None], optional):
            - List of column names to parse as dates.
            - Dict of ``{column_name: format string}`` where format string is
            strftime compatible in case of parsing string times or is one of
            (D, s, ns, ms, us) in case of parsing integer timestamps.
            - Dict of ``{column_name: arg dict}``, where the arg dict corresponds
            to the keyword arguments of :func:`pandas.to_datetime`

            Defaults to None.
        params (Union[dict, None], optional): Parameters to pass to execute method.
            Defaults to None.
        backend (str, optional) : 'pandas' to run a SQL query and return a
            `pandas.DataFrame` or 'geopandas' to run a PostGIS query and return a
            `geopandas.GeoDataFrame`. Defaults to 'pandas'.
        geom_col (str, optional): column name to convert to shapely geometries when
            `backend` is 'geopandas'. Ignored when `backend` is 'pandas'. Defaults to
            'geom'.
        crs (Union[None, str], optional) : CRS to use for the returned GeoDataFrame;
            if not set, tries to determine CRS from the SRID associated with the first
            geometry in the database, and assigns that to all geometries. Ignored when
            `backend` is 'pandas'. Defaults to None.

    Returns:
        Union[pd.DataFrame, gpd.GeoDataFrame]: Query results
    """

    res = read_saved_query(
        connection,
        query_filepath,
        parse_dates=parse_dates,
        params=params,
        backend=backend,
        geom_col=geom_col,
        crs=crs,
    )

    if dtypes:
        res = res.astype(dtypes)

    return res


def load(
    df: Union[pd.DataFrame, gpd.GeoDataFrame],
    *,
    connection: Connection,
    table_name: str,
    schema: str,
    logger: logging.Logger,
    how: str = "replace",
    pg_array_columns: list = None,
    handle_array_conversion_errors: bool = True,
    value_on_array_conversion_error: str = "{}",
    jsonb_columns: list = None,
    table_id_column: str = None,
    df_id_column: str = None,
    nullable_integer_columns: list = None,
    timedelta_columns: list = None,
    init_ddls: List[DDL] = None,
    end_ddls: List[DDL] = None,
):
    """
    Load a DataFrame or GeoDataFrame to a database table using sqlalchemy. The table
    must already exist in the database.

    Args:
        df (Union[pd.DataFrame, gpd.GeoDataFrame]): data to load
        table_name (str): name of the table
        schema (str): database schema of the table
        logger (logging.Logger): logger instance
        how (str): one of
          - 'replace' to delete all rows in the table before loading
          - 'append' to append the data to rows already in the table
          - 'upsert' to append the rows to the table, replacing the rows whose id is
            already
        pg_array_columns (list, optional): columns containing sequences that must be
          serialized before loading into columns with Postgresql `Array` type
        handle_array_conversion_errors (bool): whether to handle or raise upon error
          during the serialization of columns to load into Postgresql `Array` columns.
          Defaults to True.
        value_on_array_conversion_error (str, optional): if
          `handle_array_conversion_errors`, the value to use when an error must be
          handled. Defaults to '{}'.
        jsonb_columns (list, optional): columns containing values that must be
          serialized before loading into columns with Postgresql `JSONB` type
        table_id_column (str, optional): name of the table column to use an id.
          Required if `how` is "upsert".
        df_id_column (str, optional): name of the DataFrame column to use an id.
          Required if `how` is "upsert".
        nullable_integer_columns (list, optional): columns containing values
          that must loaded into columns with Postgresql `Integer` type. If these
          columns contain `NA` values, pandas will automatically change the dtype to
          `float` and the loading into Postgreql `Integer` columns will fail, so it is
          necessary to serialize these values as `Integer`-compatible `str` objects.
        timedelta_columns (list, optional): columns containing `Timedelta` values to
          load into Postgresql `Interval` columns. If these columns contain `NaT`
          values, the loading will fail, so it is necessary to serialize these values
          as `Interval`-compatible `str` objects.
        connection (Connection): Database connection to use for the insert
          operation.
        init_ddls: (List[DDL], optional): If given, these DDLs will be executed before
          the loading operation. Defaults to None.
        end_ddls: (List[DDL], optional): If given, these DDLs will be executed after
          the loading operation. Defaults to None.
    """
    if connection is None:
        raise ValueError("A connection must be provided")

    df = prepare_df_for_loading(
        df,
        logger,
        pg_array_columns=pg_array_columns,
        handle_array_conversion_errors=handle_array_conversion_errors,
        value_on_array_conversion_error=value_on_array_conversion_error,
        jsonb_columns=jsonb_columns,
        nullable_integer_columns=nullable_integer_columns,
        timedelta_columns=timedelta_columns,
    )

    load_with_connection(
        df=df,
        connection=connection,
        table_name=table_name,
        schema=schema,
        logger=logger,
        how=how,
        table_id_column=table_id_column,
        df_id_column=df_id_column,
        init_ddls=init_ddls,
        end_ddls=end_ddls,
    )


def load_with_connection(
    df: Union[pd.DataFrame, gpd.GeoDataFrame],
    *,
    connection: Connection,
    table_name: str,
    schema: str,
    logger: logging.Logger,
    how: str = "replace",
    table_id_column: Union[None, str] = None,
    df_id_column: Union[None, str] = None,
    init_ddls: List[DDL] = None,
    end_ddls: List[DDL] = None,
):
    if init_ddls:
        for ddl in init_ddls:
            connection.execute(ddl)

    table = get_table(table_name, schema, connection, logger)
    if how == "replace":
        # Delete all rows from table
        delete(table, connection, logger)

    elif how == "upsert":
        # Delete rows that are in the DataFrame from the table

        try:
            assert df_id_column is not None
        except AssertionError:
            raise ValueError("df_id_column cannot be null if how='upsert'")
        try:
            assert table_id_column is not None
        except AssertionError:
            raise ValueError("table_id_column cannot be null if how='upsert'")

        ids_to_delete = set(df[df_id_column].unique())

        delete_rows(
            table=table,
            id_column=table_id_column,
            ids_to_delete=ids_to_delete,
            connection=connection,
            logger=logger,
        )

    elif how == "append":
        # Nothing to do
        pass

    else:
        raise ValueError(f"how must be 'replace', 'upsert' or 'append', got {how}")

    # Insert data into table
    logger.info(f"Loading into {schema}.{table_name}")

    if isinstance(df, gpd.GeoDataFrame):
        logger.info("GeodateFrame detected, using to_postgis")
        df.to_postgis(
            name=table_name,
            con=connection,
            schema=schema,
            index=False,
            if_exists="append",
        )

    elif isinstance(df, pd.DataFrame):
        df.to_sql(
            name=table_name,
            con=connection,
            schema=schema,
            index=False,
            method=psql_insert_copy,
            if_exists="append",
        )

    else:
        raise ValueError("df must be DataFrame or GeoDataFrame.")

    if end_ddls:
        for ddl in end_ddls:
            connection.execute(ddl)


def create_table_from_geodataframe(
    gdf: gpd.GeoDataFrame,
    connection: Connection,
    table_name: str,
    schema: str = "public",
    recreate: bool = False,
    logger: logging.Logger = None,
    srs: int = None,
):
    """
    Creates a table in a PostgreSQL database from a GeoDataFrame.

    Parameters:
    - conn: Connection object to the PostgreSQL database (from sqlalchemy).
    - table_name: Name of the table to be created.
    - gdf: GeoDataFrame containing the data and column definitions.
    - schema: Name of the schema where the table will be created.
    - recreate: If True, the table will be dropped and recreated if it already exists.
    - logger: Logger object to log messages.
    - srs: EPSG code of the spatial reference system of the geometry column.
    """
    dtype_mapping = {
        "int64": "INTEGER",
        "float64": "DOUBLE PRECISION",
        "object": "TEXT",
        "datetime64[ns]": "TIMESTAMP",
        "geometry": "GEOMETRY",
    }

    if recreate:
        recreate_query = f"DROP TABLE IF EXISTS {schema}.{table_name};"
        connection.execute(text(recreate_query))

    geometry_type = gdf.geom_type.iloc[
        0
    ].upper()  # Convert to uppercase (e.g., 'POINT', 'POLYGON')
    crs = gdf.crs

    # Extract the EPSG code from the CRS, if available
    # Use srs if provided, otherwise try to extract it from the GeoDataFrame
    srid = srs if srs else crs.to_epsg() if crs else None

    # Start creating the CREATE TABLE statement
    create_table_query = f"CREATE TABLE IF NOT EXISTS {schema}.{table_name} (\n"

    # Add columns to the CREATE TABLE statement based on GeoDataFrame
    for column_name, dtype in gdf.dtypes.items():
        if column_name == gdf.geometry.name:
            # Define the geometry column with type and SRID
            pg_type = f"GEOMETRY({geometry_type}"
            if srid:
                pg_type += f", {srid}"
            pg_type += ")"
        else:
            pg_type = dtype_mapping.get(str(dtype), "TEXT")
        create_table_query += f"    {column_name} {pg_type},\n"

    # Remove the last comma and add the closing parenthesis
    create_table_query = create_table_query.rstrip(",\n") + "\n);"

    connection.execute(text(create_table_query))
