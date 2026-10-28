import os
from pathlib import Path

from prefect import flow
from shared_tasks.config import QUERIES_DIR, TEMP_DIR
from shared_tasks.file_utils import copy_directory
from shared_tasks.logging_config import get_logger

from .tasks.clean_after_imports import clean_db, clean_temp_dir
from .tasks.create_unites_foncieres import flow_create_unites_foncieres
from .tasks.download_cadastre import (
    download_bati_for_communes,
    download_cadastre_for_communes,
    download_sections_for_communes,
)
from .tasks.format_cadastre import (
    execute_format_cadastre,
    execute_init_bati,
    execute_init_cadastre,
    execute_init_sections,
)
from .tasks.format_majic import (
    clean_with_drop_db_for_majic_import,
    execute_format_majic_scripts,
    init_db_for_majic_import,
)
from .tasks.import_majic import import_majic_files
from .tasks.merge_majic_cadastre import execute_merge_cadastre_majic_scripts
from .tasks.move_data_to_import_schema import (
    flow_import_bati,
    flow_import_local,
    flow_import_parcelles,
    flow_import_proprietaire,
    flow_import_sections,
)

logger = get_logger(__name__)

STEPS_FLOW_CADASTRE = {
    "step1": {
        "description": "Copie des scripts SQL dans le répertoire temporaire",
        "default": True,
        "tasks": [
            lambda: copy_directory(
                os.path.join(QUERIES_DIR, "majic"), os.path.join(TEMP_DIR, "sql")
            )
        ],
    },
    "step2": {
        "description": "Import des données brutes dans MAJIC_SCHEMA",
        "default": True,
        "tasks": [lambda dirname: import_majic_files(dirname)],
    },
    "step3": {
        "description": "Suppression des anciennes tables métiers MAJIC",
        "default": True,
        "tasks": [clean_with_drop_db_for_majic_import],
    },
    "step4": {
        "description": "Initialisation des tables métiers dans MAJIC_SCHEMA",
        "default": True,
        "tasks": [init_db_for_majic_import],
    },
    "step5": {
        "description": "Formatage et traitement des données MAJIC",
        "default": True,
        "tasks": [execute_format_majic_scripts],
    },
    "step6": {
        "description": "Téléchargement et import des géométries cadastrales",
        "default": True,
        "tasks": [
            execute_init_cadastre,
            download_cadastre_for_communes,
            execute_format_cadastre,
        ],
    },
    "step7": {
        "description": "Consolidation Cadastre × MAJIC dans IMPORT_SCHEMA",
        "default": True,
        "tasks": [execute_merge_cadastre_majic_scripts],
    },
    "step8": {
        "description": "Création des unités foncières",
        "default": True,
        "tasks": [flow_create_unites_foncieres],
    },
    "step9": {
        "description": (
            "Copie des parcelles, propriétaires et locaux dans IMPORT_SCHEMA"
        ),
        "default": True,
        "tasks": [flow_import_parcelles, flow_import_proprietaire, flow_import_local],
    },
    "step10": {
        "description": "Téléchargement et import des géométries des bâtiments",
        "default": True,
        "tasks": [execute_init_bati, download_bati_for_communes],
    },
    "step11": {
        "description": "Copie des bâtiments dans IMPORT_SCHEMA",
        "default": True,
        "tasks": [flow_import_bati],
    },
    "sections": {
        "description": "Import des sections cadastrales",
        "default": True,
        "tasks": [
            lambda: copy_directory(
                os.path.join(QUERIES_DIR, "majic"), os.path.join(TEMP_DIR, "sql")
            ),
            execute_init_sections,
            download_sections_for_communes,
            flow_import_sections,
        ],
    },
    "step12": {
        "description": "Nettoyage des fichiers temporaires et de MAJIC_SCHEMA",
        "default": True,
        "tasks": [clean_temp_dir, clean_db],
    },
}


@flow
def import_cadastre_majic_flow(path: Path, enabled_steps: list[str]):
    """
    Exécute les étapes sélectionnées du flux Cadastre × MAJIC.
    """
    # Check if the path exists
    if path is None or not os.path.isdir(path):
        logger.error(
            "Le chemin spécifié n'est pas un répertoire existant. "
            "Veuillez vérifier le chemin et réessayer."
        )
        return

    logger.info("Le répertoire existe. Lancement du traitement.")
    temp_dir = os.path.join(os.getcwd(), "temp")
    logger.info(f"Répertoire temporaire : {temp_dir}")
    logger.info("----------------")

    for step_name, step in STEPS_FLOW_CADASTRE.items():
        if step_name in enabled_steps:
            logger.info(f"Exécution de l'étape {step_name} : {step['description']}")
            for task in step["tasks"]:
                # Pass `path` to tasks that accept it
                if "dirname" in task.__code__.co_varnames:
                    task(path)
                else:
                    task()
        else:
            logger.info(f"Étape ignorée {step_name} : {step['description']}")

    logger.info("Traitement terminé avec succès.")
