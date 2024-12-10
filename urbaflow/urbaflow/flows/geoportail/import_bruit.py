# %%
from owslib.wfs import WebFeatureService
import geopandas as gpd
from io import BytesIO

from prefect import flow, get_run_logger, task

from urbaflow.urbaflow.shared_tasks.etl_gpd_utils import (
    create_table_from_geodataframe,
    load,
)
from urbaflow.urbaflow.shared_tasks.db_engine import create_engine

# https://geoservices.ign.fr/services-web-experts-transports#2314
# Données "transports" en WFS

wfs_url_geoplateforme = "https://data.geopf.fr/annexes/ressources/wfs/transports.xml"

# DGAC - PEB (Plans d'exposition aux bruits)
layername_peb = "DGAC-PEB_BDD_FXX_WM:fxx_peb_wm"

# DGAC - PGS (Plans de gêne sonore)
layername_pgs = "DGAC-PGS_BDD_FXX_WM:fxx_pgs_wm"


@task
def download_wfs_data(wfs_url, layername) -> gpd.GeoDataFrame:
    """
    Download data from a WFS service and return a GeoDataFrame
    """
    wfs = WebFeatureService(url=wfs_url, version="2.0.0")
    response = wfs.getfeature(typename=layername, outputFormat="application/json")

    geo_df = gpd.read_file(BytesIO(response.read()))

    return geo_df


@flow
def import_bruit(schema="public"):
    logger = get_run_logger()
    e = create_engine()
    peb = download_wfs_data(wfs_url_geoplateforme, layername_peb)
    with e.begin() as conn:
        create_table_from_geodataframe(
            gdf=peb,
            connection=conn,
            table_name="bruit_peb",
            schema=schema,
            logger=logger,
            recreate=True,
            srs=2154,
        )
        load(
            peb.to_crs("EPSG:2154"),
            connection=conn,
            table_name="bruit_peb",
            schema=schema,
            how="replace",
            logger=logger,
        )
    pgs = download_wfs_data(wfs_url_geoplateforme, layername_pgs)
    with e.begin() as conn:
        create_table_from_geodataframe(
            gdf=pgs,
            connection=conn,
            table_name="bruit_pgs",
            schema=schema,
            logger=logger,
            recreate=True,
            srs=2154,
        )
        load(
            pgs.to_crs("EPSG:2154"),
            connection=conn,
            table_name="bruit_pgs",
            schema=schema,
            how="replace",
            logger=logger,
        )


# %%
import_bruit._run()
# %%
