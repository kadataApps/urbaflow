from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import logger
from shared_tasks.sql_query_utils import replace_parameters_in_script
from shared_tasks.config import TEMP_DIR


def clean_with_drop_db_for_majic_import():
    """
    Suppression des tables métiers (QgisCadastre) pour import des données MAJIC brutes
    """
    logger.info(
        "Nettoyage base de données - Suppression tables métiers MAJIC - cf.QgisCadastre"
    )
    script_path = TEMP_DIR / "sql/commun_drop_metier.sql"
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path, connection=conn)
    logger.info(
        "Base de données prête pour initialisation avec les tables métiers MAJIC."
    )


def init_db_for_majic_import():
    """
    Création des tables métiers (QgisCadastre) pour import des données MAJIC brutes
    """
    logger.info(
        "Initialisation base de données - tables métiers MAJIC - cf.QgisCadastre"
    )
    script_path_create = TEMP_DIR / "sql/commun_create_metier.sql"
    script_path_nomenclature = TEMP_DIR /"sql/commun_insert_nomenclature.sql"
    
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
        run_sql_script(sql_filepath=script_path_nomenclature, connection=conn)
    logger.info("Base de données initialisée avec les tables métiers MAJIC.")


def execute_format_majic_scripts():
    """
    Execute dans postgis les scripts de formatage des données MAJIC.
    Scripts QgisCadastre (import + formatage MAJIC dans tables métiers)
    + scripts KADATA (calculs indicateurs et croisements)
    """
    annee = "2019"
    lot = ""
    replace_dict = {"[ANNEE]": annee, "[LOT]": lot}

    logger.info("Execution des scripts de formatage des données MAJIC")
    script_list = [
        "2019/majic3_formatage_donnees.sql",
        "traitements/majic/0-renommage_tables.sql",
        "traitements/majic/1-traitement_qualification_proprietaires.sql",
        "traitements/majic/2-traitement_local_pev.sql",
        "traitements/majic/3-traitement_lots.sql",
        "traitements/majic/4-traitement_suf.sql",
        "traitements/majic/5-proprietaire_local10_update_gdprop.sql",
    ]

    e = create_engine()
    with e.begin() as conn:
        scripts_count = len(script_list)
        etape = 0
        sql_scripts_dir = TEMP_DIR / "sql"
        for script in script_list:
            etape += 1
            logger.info(
                "Etape " + str(etape) + "/" + str(scripts_count) + " : " + script
            )
            script_path = sql_scripts_dir / script
            replace_parameters_in_script(script_path, replace_dict)
            run_sql_script(sql_filepath=script_path, connection=conn)

    logger.info("Formatage terminé.")
