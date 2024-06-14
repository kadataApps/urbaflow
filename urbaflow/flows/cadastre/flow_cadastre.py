import sys
import os
from pathlib import Path

from utils.script_utils import copy_files_to_temp

from .tasks.import_majic import majicImport
from .tasks.format_majic import (
    clean_with_drop_db_for_majic_import,
    init_db_for_majic_import,
    execute_format_majic_scripts,
)
from .tasks.download_cadastre import (
    download_cadastre_for_communes,
    download_bati_for_communes,
)
from .tasks.format_cadastre import (
    execute_init_cadastre,
    execute_format_cadastre,
    execute_init_bati,
)
from .tasks.merge_majic_cadastre import execute_merge_cadastre_majic_scripts
from .tasks.get_communes_majic import write_communes_to_file
from .tasks.import_to_public import (
    flow_import_bati,
    flow_import_parcelles,
    flow_import_proprietaire,
    flow_import_local,
)
from .tasks.clean_after_imports import clean_temp_dir, clean_db


STEPS_FLOW_CADASTRE = {
    "1": {
        "description": "Import données brutes (6 fichiers) dans 6 tables temporaires dans PostgreSQL",
        "default": True,
    },
    "2": {
        "description": "Copie des scripts dans le répertoire temporaire (pour adaptation des scripts en fonction des paramètres d'import)",
        "default": True,
    },
    "3": {"description": "Suppression des tables métiers", "default": True},
    "4": {
        "description": "Initialisation de la base avec tables métiers",
        "default": True,
    },
    "5": {"description": "Formatage des données MAJIC", "default": True},
    "6": {
        "description": "Identification des communes importées via MAJIC",
        "default": True,
    },
    "7": {
        "description": "Téléchargement et import des données cadastre (vecteurs)",
        "default": True,
    },
    "8": {"description": "Fusion des données Cadastre et MAJIC", "default": True},
    "9": {
        "description": "Intégration des données parcelles, proprietaires, et local dans Public",
        "default": True,
    },
    "10": {
        "description": "Téléchargement et import des données bati (vecteurs)",
        "default": True,
    },
    "11": {"description": "Intégration des données bati dans Public", "default": True},
    "12": {
        "description": "Nettoyage des fichiers temporaires et des tables",
        "default": True,
    },
}


def flow_import_majic_to_postgres(path):
    """
    Etape 1 - Import des données MAJIC dans PostgreSQL
    à partir des 6 fichiers bruts
    dans 6 tables "temporaires"
    """
    majicImp = majicImport(path)
    print("Import des données MAJIC dans PostgreSQL")
    majicImp.importMajic()


def flow_copy_transform_majic_queries():
    print("Copie des scripts dans le répertoire temporaire:")
    sql_scripts_dir = os.path.join(
        Path(__file__).resolve().parent.parent.parent, "queries/majic/"
    )
    sqlScriptsDestDir = os.path.join(os.getcwd(), "temp/sql/")
    print("Source: ", sql_scripts_dir)
    print("Destination: ", sqlScriptsDestDir)
    copy_files_to_temp(sql_scripts_dir, sqlScriptsDestDir)
    print("Scripts copiés dans le répertoire temporaire.")


def flow_clean_db_for_majic():
    clean_with_drop_db_for_majic_import()


def flow_init_db_for_majic_import():
    init_db_for_majic_import()


def flow_transform_majic_data():
    execute_format_majic_scripts()


def flow_write_imported_communes_to_file():
    write_communes_to_file()


def flow_import_cadastre_geometries():
    execute_init_cadastre()
    download_cadastre_for_communes()
    execute_format_cadastre()


def flow_merge_cadastre_with_majic():
    execute_merge_cadastre_majic_scripts()


def flow_export_tables_to_public_schema():
    flow_import_parcelles()
    flow_import_proprietaire()
    flow_import_local()


def flow_download_bati_geometries():
    execute_init_bati()
    download_bati_for_communes()


def flow_import_bati_geometries():
    flow_import_bati()


def flow_clean():
    clean_temp_dir()
    clean_db()


def flow_cadastre(path, steps):
    # Check if path exits
    if path is not None and os.path.isdir(path):
        print("Path is dir and exists. We proceed.")
        tempDir = os.path.join(os.getcwd(), "temp")
        print(tempDir)
        print("----------------")
        if steps["1"]["default"] is True:
            flow_import_majic_to_postgres(path)

        if steps["2"]["default"] is True:
            flow_copy_transform_majic_queries()

        if steps["3"]["default"] is True:
            flow_clean_db_for_majic()

        if steps["4"]["default"] is True:
            flow_init_db_for_majic_import()

        if steps["5"]["default"] is True:
            flow_transform_majic_data()

        if steps["6"]["default"] is True:
            flow_write_imported_communes_to_file()

        if steps["7"]["default"] is True:
            flow_import_cadastre_geometries()

        if steps["8"]["default"] is True:
            flow_merge_cadastre_with_majic()

        if steps["9"]["default"] is True:
            flow_export_tables_to_public_schema()

        if steps["10"]["default"] is True:
            flow_download_bati_geometries()

        if steps["11"]["default"] is True:
            flow_import_bati_geometries()
        if steps["12"]["default"] is True:
            flow_clean()

        print("Fin des scripts d'import")
    else:
        print(
            "Le chemin spécifié n'est pas un répertoire existant. Veuillez vérifier le chemin et réessayer.)"
        )


if __name__ == "__main__":
    path = None
    try:
        path = sys.argv[1]
    except Exception:
        print("error")

    print("Will try to import majic files from dir: ")
    print(path)
    flow_cadastre(path, steps=STEPS_FLOW_CADASTRE)
