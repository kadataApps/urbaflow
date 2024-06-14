import gzip
import os, ast
import sys
import urllib.request

from utils.dbutils import importGeoJSON
from .get_communes_majic import get_imported_communes_from_file


def reporthook(blocknum, blocksize, totalsize):
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r%5.1f%% %*d / %d" % (
            percent, len(str(totalsize)), readsofar, totalsize)
        sys.stderr.write(s)
        if readsofar >= totalsize:  # near the end
            sys.stderr.write("\n")
    else:  # total size is unknown
        sys.stderr.write("read %d\n" % (readsofar,))

def downloadCadastre(codeinsee: str, targetDir, millesime):
    param_millesime =  'latest' if millesime is None else millesime 
    url = 'https://cadastre.data.gouv.fr/data/etalab-cadastre/'+param_millesime+'/geojson/communes/'
    # url = 'https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/'
    url += codeinsee[0:2] + '/'+ codeinsee
    url += '/cadastre-'+codeinsee
    url += '-parcelles.json.gz'
    # https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/77/77111/cadastre-77111-parcelles.json.gz

    file_name = url.split('/')[-1]
    
    if not (os.path.exists(targetDir)):
        os.makedirs(targetDir)
    destFileName = os.path.join(targetDir, file_name)
    urllib.request.urlretrieve(url, destFileName, reporthook)
    unzipCadastre(destFileName)
    return destFileName


def downloadBati(codeinsee, targetDir):
    url = 'https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/'
    url += codeinsee[0:2] + '/' + codeinsee
    url += '/cadastre-'+codeinsee
    url += '-batiments.json.gz'
    # https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/77/77111/cadastre-77111-bati.json.gz

    file_name = url.split('/')[-1]

    if not (os.path.exists(targetDir)):
        os.makedirs(targetDir)
    destFileName = os.path.join(targetDir, file_name)
    urllib.request.urlretrieve(url, destFileName, reporthook)
    unzipCadastre(destFileName)
    return destFileName


def downloadCadastreForCommunes():
    tempDir = os.path.join(os.getcwd(), 'temp/downloads/')
    config = get_imported_communes_from_file()
    try:
        communes = ast.literal_eval(config["communes"])
    except:
        print("Aucune commune dans le fichier communes.txt. Rien à télécharger")
    else:
        millesime = os.getenv("CADASTRE_MILLESIME")
        print(communes)
        for commune in communes:
            print(commune)
            downloadCadastre(commune, tempDir, millesime)
            file = os.path.join(
                tempDir, 'cadastre-%s-parcelles.json' % commune)
            json = importGeoJSON()
            json.importFile(file, 'cadastre_parcelles')


def downloadBatiForCommunes():
    tempDir = os.path.join(os.getcwd(), 'temp/downloads/')
    config = get_imported_communes_from_file()
    try:
        communes = ast.literal_eval(config["communes"])
    except:
        print("Aucune commune dans le fichier communes.txt. Rien à télécharger")   
    else:
        print(communes)
        for commune in communes:
            print(commune)
            downloadBati(commune, tempDir)
            file = os.path.join(
                tempDir, 'cadastre-%s-batiments.json' % commune)
            json = importGeoJSON()
            json.importFile(file, 'cadastre_bati')


def unzipCadastre(archivePath):
    # get directory where archivePath is stored
    dir = os.path.dirname(archivePath)
    # filename = os.path.basename(archivePath)  # get filename
    file_json, file_json_ext = os.path.splitext(archivePath) # split into file.json and .gz

    src_name = archivePath
    dest_name = os.path.join(dir, file_json)
    with gzip.open(src_name, 'rb') as infile:
        with open(dest_name, 'wb') as outfile:
            for line in infile:
                outfile.write(line)
