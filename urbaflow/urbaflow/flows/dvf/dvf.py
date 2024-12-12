from pathlib import Path
import urllib.request

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from shared_tasks.etl_file_utils import unzip_file_in_place
from shared_tasks.report_hook import reporthook
from shared_tasks.logging_config import get_logger


# https://github.com/ESO-Rennes/Analyse-Donnees-DVF


@task(retries=3, retry_delay_seconds=10)
def download_dvf_by_dep_year(departement: str, year: int, tagert_dir: Path):
    """
    Download csv from Etalab
    Exemple d'url: https://files.data.gouv.fr/geo-dvf/latest/csv/2024/departements/01.csv.gz

    Args:
        departement : numéro du département sur 2 ou 3 caractères
        year : année sur 4 caractères
        tagert_dir : Path
    """
    logger = get_logger()
    DVF_BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/"
    url = f"{DVF_BASE_URL}{year}/departements/{departement}.csv.gz"

    file_name = f"dvf_{departement}_{year}.csv.gz"

    tagert_dir.mkdir(parents=True, exist_ok=True)

    dest_filename = tagert_dir / file_name
    logger.info(f"Downloading {url} to {dest_filename}")
    urllib.request.urlretrieve(url, dest_filename, reporthook)
    unzip_file_in_place(dest_filename)
    return dest_filename


@task
def download_dvf_by_dep(dep: str, tagert_dir: Path):
    years = range(2019, 2024)
    for year in years:
        download_dvf_by_dep_year.submit(dep, year, tagert_dir)


@flow(name="import DVF", task_runner=ConcurrentTaskRunner())
def dvf_flow(departments: str, tagert_dir: Path):
    departments_list = departments.split(",")
    for dep in departments_list:
        download_dvf_by_dep.submit(dep, tagert_dir)
