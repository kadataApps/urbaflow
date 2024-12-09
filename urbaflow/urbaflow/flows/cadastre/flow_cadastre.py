import os
from pathlib import Path
from typing import List

from prefect import flow

from urbaflow.logging_config import logger
from urbaflow.utils.script_utils import copy_files_to_temp

from .tasks.import_majic import import_majic
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
    "step1": {
        "description": "Import raw MAJIC data into temporary PostgreSQL tables",
        "default": True,
        "tasks": [lambda dirname: import_majic(dirname).import_majic_files()],
    },
    "step2": {
        "description": "Copy SQL scripts to the temp directory",
        "default": True,
        "tasks": [lambda: copy_files_to_temp("queries/majic", "temp/sql")],
    },
    "step3": {
        "description": "Drop existing tables before importing new MAJIC data",
        "default": True,
        "tasks": [clean_with_drop_db_for_majic_import],
    },
    "step4": {
        "description": "Initialize database for MAJIC data import",
        "default": True,
        "tasks": [init_db_for_majic_import],
    },
    "step5": {
        "description": "Format and process MAJIC data",
        "default": True,
        "tasks": [execute_format_majic_scripts],
    },
    "step6": {
        "description": "Identify imported communes and write to file",
        "default": True,
        "tasks": [write_communes_to_file],
    },
    "step7": {
        "description": "Download and import cadastre geometries",
        "default": True,
        "tasks": [execute_init_cadastre, download_cadastre_for_communes, execute_format_cadastre],
    },
    "step8": {
        "description": "Merge cadastre data with MAJIC",
        "default": True,
        "tasks": [execute_merge_cadastre_majic_scripts],
    },
    "step9": {
        "description": "Export parcel, owner, and local data to the public schema",
        "default": True,
        "tasks": [flow_import_parcelles, flow_import_proprietaire, flow_import_local],
    },
    "step10": {
        "description": "Download and import building geometries",
        "default": True,
        "tasks": [execute_init_bati, download_bati_for_communes],
    },
    "step11": {
        "description": "Export building data to the public schema",
        "default": True,
        "tasks": [flow_import_bati],
    },
    "step12": {
        "description": "Clean up temporary files and database tables",
        "default": True,
        "tasks": [clean_temp_dir, clean_db],
    },
}


@flow(name="import cadastre et majic")
def import_cadastre_majic_flow(path: Path, enabled_steps: List[str]):
    """
    Execute the cadastre workflow based on the given steps.

    Args:
        path (str): Path to the directory containing MAJIC files.
        steps (dict): A dictionary defining which steps to execute.
    """
    # Check if the path exists
    if path is None or not os.path.isdir(path):
        logger.error(
            "Le chemin spécifié n'est pas un répertoire existant. Veuillez vérifier le chemin et réessayer."
        )
        return

    logger.info("Path is a valid directory. Proceeding with the workflow.")
    temp_dir = os.path.join(os.getcwd(), "temp")
    logger.info(f"Temporary directory: {temp_dir}")
    logger.info("----------------")

    for step_name, step  in STEPS_FLOW_CADASTRE.items():
        if step_name in enabled_steps:
            logger.info(f"Executing Step {step_name}: {step['description']}")
            for task in step["tasks"]:
                # Pass `path` to tasks that accept it
                if "dirname" in task.__code__.co_varnames:
                    task(path)
                else:
                    task()
        else:
            logger.info(f"Skipping Step {step_name}: {step['description']}")

    logger.info("Workflow completed successfully.")


# if __name__ == "__main__":
#     path = None
#     try:
#         path = sys.argv[1]
#     except Exception:
#         logger.info("error")

#     logger.info("Will try to import majic files from dir: ")
#     logger.info(path)
#     flow_cadastre(path, steps=STEPS_FLOW_CADASTRE.keys())
