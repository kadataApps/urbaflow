from pathlib import Path
import requests
import zipfile
import io
import pandas as pd

from prefect import Flow, task

from shared_tasks.etl import run_sql_script
from utils.config import LIBRARY_LOCATION
from utils.db_config import create_engine

URL_GEOSIRENE = "https://files.data.gouv.fr/insee-sirene-geo/GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.zip"

# le fichier stock des unités légales (unités légales actives et cessées dans leur état courant au répertoire)
# https://files.data.gouv.fr/insee-sirene/StockUniteLegale_utf8.zip

# Fichier StockEtablissement
# (établissements actifs et fermés dans leur état courant au répertoire)
# https://files.data.gouv.fr/insee-sirene/StockEtablissement_utf8.zip


# https://files.data.gouv.fr/geo-sirene/last/dep/
# https://files.data.gouv.fr/geo-sirene/last/dep/geo_siret_88.csv.gz


DATA_PATH = "data/geosirene"


@task
def download_geosirene():
    """
    Download the geosirene data from the given URL and extract it to the data/geosirene folder.
    """
    r = requests.get(URL_GEOSIRENE)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(LIBRARY_LOCATION / "data/geosirene")


@task
def import_geosirene(file_path: str):
    e = create_engine("local")
    chunksize = 10000  # Number of rows per chunk
    for chunk in pd.read_csv(
        LIBRARY_LOCATION / "data/geosirene" / file_path, chunksize=chunksize
    ):
        chunk.to_sql("geosirene", e, if_exists="append", index=False, method="multi")


with Flow("Import Geosirene") as flow:
    # download_geosirene()
    # file = 'GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.csv'
    file = "geo_siret_88.csv"
    # import_geosirene(file_path=file)
    run_sql_script(LIBRARY_LOCATION / "pipeline/queries/geosirene/create_geom.sql")

flow.file_name = Path(__file__).name
