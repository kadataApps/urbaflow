# %%
from prefect import task
import requests
import zipfile
from urbaflow.urbaflow.shared_tasks.logging_config import logger


@task
def extract_unite_legale():
    """
    Download and extract the unite legale file

    le fichier stock des unités légales (unités légales actives et cessées dans leur état courant au répertoire)
    https://files.data.gouv.fr/insee-sirene/StockUniteLegale_utf8.zip
    """
    logger.info("Downloading and extracting unite legale file")
    url = "https://files.data.gouv.fr/insee-sirene/StockUniteLegale_utf8.zip"
    response = requests.get(url)
    with open("StockUniteLegale_utf8.zip", "wb") as f:
        f.write(response.content)
    with zipfile.ZipFile("StockUniteLegale_utf8.zip", "r") as zip_ref:
        zip_ref.extractall("StockUniteLegale_utf8")
    return "StockUniteLegale_utf8"


# %%
