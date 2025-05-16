from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import get_logger
from shared_tasks.sql_query_utils import replace_parameters_in_script
from shared_tasks.config import TEMP_DIR


def execute_merge_cadastre_majic_scripts():
    """
    Execute dans postgis les scripts permettant de
    fusionner les données MAJIC et cadastre dans une seule table
    """
    logger = get_logger()

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
        "traitements/qualification/2-parcellaire_update_proprietaires.sql",
    ]

    scripts_count = len(script_list)
    etape = 0
    sql_scripts_dir = TEMP_DIR / "sql"
    e = create_engine()
    with e.begin() as conn:
        for script in script_list:
            etape += 1
            logger.info(
                "Etape " + str(etape) + "/" + str(scripts_count) + " : " + script
            )
            script_path = sql_scripts_dir / script
            replace_parameters_in_script(script_path, replace_dict)
            run_sql_script(sql_filepath=script_path, connection=conn)
    logger.info("Fusion Cadastre x MAJIC terminée.")
