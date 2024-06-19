import os

from logging_config import logger
from utils.script_utils import replace_parameters_in_script
from utils.dbutils import pg_connection


def execute_merge_cadastre_majic_scripts():
    """
    Execute dans postgis les scripts permettant de
    fusionner les données MAJIC et cadastre dans une seule table
    """
    annee = "2019"
    lot = ""
    replace_dict = {"[ANNEE]": annee, "[LOT]": lot}

    logger.info("Execution des scripts de fusion Cadastre x MAJIC")
    script_list = [
        "traitements/merge/0-creation_table_parcellaire.sql",
        "traitements/merge/1-affectation_proprietaire.sql",
        "traitements/merge/2-affectation_local_pev.sql",
        "traitements/merge/3-affectation_adresses.sql",
        "traitements/merge/4-anonymisation.sql",
        "traitements/qualification/0-correction_typologie_proprietaire_create.sql",
        "traitements/qualification/1-proprietaire_update_catpro.sql",
        "traitements/qualification/2-parcellaire_update_proprietaires.sql",
        "traitements/qualification/3-proprietaire_update_gdprop",
    ]

    scripts_count = len(script_list)
    etape = 0
    sql_scripts_dir = os.path.join(os.getcwd(), "temp/sql/")
    conn = pg_connection()
    for script in script_list:
        etape += 1
        logger.info("Etape " + str(etape) + "/" + str(scripts_count) + " : " + script)
        script_path = os.path.join(sql_scripts_dir, script)
        replace_parameters_in_script(script_path, replace_dict)
        conn.execute_script(script_path)
    conn.close_connection()
    logger.info("Fusion Cadastre x MAJIC terminée.")
