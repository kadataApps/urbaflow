# COPYRIGHT Vincent Chery - MonitorEnv

from pathlib import Path
from typing import Optional, Union

import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection


def read_saved_query(
    connection: Connection,
    sql_filepath: Union[str, Path],
    chunksize: Optional[str] = None,
    parse_dates: Optional[list | dict] = None,
    params: Union[None, dict] = None,
    backend: str = "pandas",
    geom_col: str = "geom",
    crs: Union[int, None] = None,
    **kwargs,
) -> pd.DataFrame | gpd.GeoDataFrame:
    """Run saved SQLquery on a database.

    Args:
        connection (Connection): SQLAlchemy connection object
        sql_filepath (str): path to .sql file, starting from the saved queries folder.
            example : "ocan/nav_fr_peche.sql"
        parse_dates (Union[list, dict, None], optional):
            - List of column names to parse as dates.
            - Dict of ``{column_name: format string}`` where format string is
            strftime compatible in case of parsing string times or is one of
            (D, s, ns, ms, us) in case of parsing integer timestamps.
            - Dict of ``{column_name: arg dict}``, where the arg dict corresponds
            to the keyword arguments of :func:`pandas.to_datetime`
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
        kwargs : passed to pd.read_sql or gpd.read_postgis

    Returns:
        Union[pd.DataFrame, gpd.DataFrame]: Query results
    """
    with open(sql_filepath, "r") as sql_file:
        query = text(sql_file.read())

    read_query(
        connection,
        query,
        chunksize=chunksize,
        params=params,
        backend=backend,
        geom_col=geom_col,
        crs=crs,
        parse_dates=parse_dates,
        **kwargs,
    )


def read_query(
    connection: Connection,
    query,
    chunksize: Union[None, str] = None,
    params: Union[dict, None] = None,
    backend: str = "pandas",
    geom_col: str = "geom",
    crs: Union[int, None] = None,
    parse_dates: Optional[list | dict] = None,
    **kwargs,
) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """Run SQLquery on a database.

    Args:
        connection (Connection): SQLAlchemy connection object
        query (str): Query string or SQLAlchemy Selectable
        chunksize (Union[None, str], optional): If specified, return an iterator where
            `chunksize` is the number of rows to include in each chunk. Defaults to None.
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
            geometry in the database, and assigns that to all geometries. Ignored when `backend`
            is 'pandas'. Defaults to None.
        parse_dates (Optional[list | dict], optional):

          - List of column names to parse as dates.
          - Dict of ``{column_name: format string}`` where format string is
            strftime compatible in case of parsing string times or is one of
            (D, s, ns, ms, us) in case of parsing integer timestamps.
          - Dict of ``{column_name: arg dict}``, where the arg dict corresponds
            to the keyword arguments of :func:`pandas.to_datetime`
        kwargs : passed to pd.read_sql or gpd.read_postgis

    Returns:
        Union[pd.DataFrame, gpd.DataFrame]: Query results
    """

    if backend == "pandas":
        return pd.read_sql(
            query,
            connection,
            chunksize=chunksize,
            params=params,
            parse_dates=parse_dates,
            **kwargs,
        )
    elif backend == "geopandas":
        return gpd.read_postgis(
            query,
            connection,
            geom_col=geom_col,
            crs=crs,
            chunksize=chunksize,
            parse_dates=parse_dates,
            params=params,
            **kwargs,
        )
    else:
        raise ValueError(f"backend must be 'pandas' or 'geopandas', got {backend}")
