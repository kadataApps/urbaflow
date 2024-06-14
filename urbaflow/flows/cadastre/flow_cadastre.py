import psycopg2
import sys
import os
from pathlib import Path

from utils.script_utils import copy_files_to_temp

from .tasks.import_majic import majicImport
from .tasks.format_majic import cleanWithDropDbForMajicImport, initDbForMajicImport, executeFormatageMajicScripts
from .tasks.download_cadastre import downloadCadastreForCommunes, downloadBatiForCommunes
from .tasks.format_cadastre import executeInitCadastre,  executeFormatageCadastre, executeInitBati
from .tasks.merge_majic_cadastre import executeMergeCadastreMajicScripts
from .tasks.get_communes_majic import write_communes_to_file
from .tasks.import_to_public import routine_import_bati, routine_import_parcelles, routine_import_proprietaire, routine_import_local
from .tasks.clean_after_imports import cleanTempDir, cleanDatabase



def flow_import_majic_to_postgres(path):
    """
     Etape 1 - Import des données MAJIC dans PostgreSQL
     à partir des 6 fichiers bruts
     dans 6 tables "temporaires"
    """
    majicImp = majicImport(path)
    print("Importing Majic Data into DB")
    majicImp.importMajic()

def flow_copy_transform_majic_queries():
    print("Copy scripts files to temp dir:")
    sqlScriptsDir = os.path.join(Path(
        __file__).resolve().parent.parent.parent, 'queries/majic/')
    sqlScriptsDestDir = os.path.join(os.getcwd(), 'temp/sql/')
    print("Source: ", sqlScriptsDir)
    print("Destination: ", sqlScriptsDestDir)
    copy_files_to_temp(sqlScriptsDir, sqlScriptsDestDir)
    print("Script Files copied")

def flow_clean_db_for_majic():
    cleanWithDropDbForMajicImport()

def flow_init_db_for_majic_import():
    initDbForMajicImport()

def flow_transform_majic_data():
    executeFormatageMajicScripts()

def flow_write_imported_communes_to_file():
    write_communes_to_file()

def flow_import_cadastre_geometries():
    executeInitCadastre()
    downloadCadastreForCommunes()
    executeFormatageCadastre()

def flow_merge_cadastre_with_majic():
     executeMergeCadastreMajicScripts()

def flow_export_tables_to_public_schema():
    routine_import_parcelles()
    routine_import_proprietaire()
    routine_import_local()

def flow_download_bati_geometries():
    executeInitBati()
    downloadBatiForCommunes()

def flow_import_bati_geometries():
    routine_import_bati()

def flow_clean():
    cleanTempDir()
    cleanDatabase()


def run_routines(path, etapes):

    # Check if path exits
    if path is not None and os.path.isdir(path):
        print("Path is dir and exists. We proceed.")
        tempDir = os.path.join(os.getcwd(), 'temp')
        print(tempDir)
        print("----------------")
        if etapes["1"]["status"] is True:
           flow_import_majic_to_postgres(path)

        if etapes["2"]["status"] is True:
            flow_copy_transform_majic_queries()

        if etapes["3"]["status"] is True:
            flow_clean_db_for_majic()

        if etapes["4"]["status"] is True:
            flow_init_db_for_majic_import()

        if etapes["5"]["status"] is True:
            flow_transform_majic_data()

        if etapes["6"]["status"] is True:
            flow_write_imported_communes_to_file()

        if etapes["7"]["status"] is True:
            flow_import_cadastre_geometries()

        if etapes["8"]["status"] is True:
           flow_merge_cadastre_with_majic()

        if etapes["9"]["status"] is True:
            flow_export_tables_to_public_schema()

        if etapes["10"]["status"] is True:
            flow_download_bati_geometries()

        if etapes["11"]["status"] is True:
            flow_import_bati_geometries()
        if etapes["12"]["status"] is True:
            flow_clean()

        print("Fin des scripts d'import")
    else:
        print('Path is not a dir or doesn''t exists')


etapes = {
    "1": {
        "description": "Import données brutes (6 fichiers) dans 6 tables temporaires dans PostgreSQL",
        "status": True
    },
    "2": {
        "description": "Copie des scripts dans le répertoire temporaire (pour adaptation des scripts en fonction des paramètres d'import)",
        "status": True
    },
    "3": {
        "description": "Suppression des tables métiers",
        "status": True
    },
    "4": {
        "description": "Initialisation de la base avec tables métiers",
        "status": True
    },
    "5": {
        "description": "Formatage des données MAJIC",
        "status": True
    },
    "6": {
        "description": "Identification des communes importées via MAJIC",
        "status": True
    },
    "7": {
        "description": "Téléchargement et import des données cadastre (vecteurs)",
        "status": True
    },
    "8": {
        "description": "Fusion des données Cadastre et MAJIC",
        "status": True
    },
    "9": {
        "description": "Intégration des données parcelles, proprietaires et local dans Public",
        "status": True
    },
    "10": {
        "description": "Téléchargement et import des données bati (vecteurs)",
        "status": True
    },
    "11": {
        "description": "Intégration des données bati dans Public",
        "status": True
    },
    "12": {
        "description": "Nettoyage des fichiers temporaires et des tables",
        "status": True
    }
}


if __name__ == '__main__':
    path = None
    try:
        path = sys.argv[1]
    except(Exception) as error:
        print('error')

    print("Will try to import majic files from dir: ")
    print(path)
    run_routines(path, etapes)


