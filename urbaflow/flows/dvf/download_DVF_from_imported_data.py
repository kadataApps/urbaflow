import gzip
import os
import ast
import urllib.request

from utils.report_hook import reporthook
from utils.dbutils import importGeoJSON
from utils.unzip_file import unzip_file_in_place

def download_DVF_by_dep_year(departement, year, targetDir):
    url = 'https://cadastre.data.gouv.fr/data/etalab-dvf/latest/csv/'
    url += year+'/departements/'
    url += departement+ '.csv.gz'

    file_name = departement + '_' + year + '.csv'

    if not (os.path.exists(targetDir)):
        os.makedirs(targetDir)
    destFileName = os.path.join(targetDir, file_name)
    urllib.request.urlretrieve(url, destFileName, reporthook)
    unzip_file_in_place(destFileName)
    return destFileName


def download_DVF_by_dep(dep, targetDir):
    years = ['2020', '2019', '2018', '2017', '2016', '2015']
    for year in years:
        download_DVF_by_dep_year(dep, year, targetDir)


def import_DVF(departements):
    """
    Download csv from Etalab
    https://cadastre.data.gouv.fr/data/etalab-dvf/latest/csv/2020/departements/
    """
    for dep in departements:
    # download dvf for requested code insee
        download_DVF_by_dep(dep)
    # upload data to postgis



def flow_dvf(dep, targetDir):
#    importDVF(dep)
    download_DVF_by_dep(dep, targetDir)

