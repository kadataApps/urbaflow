import os

from utils.script_utils import replace_parameters_in_script
from utils.dbutils import pg_connection


def clean_with_drop_db_for_majic_import():
    """
    Suppression des tables métiers (QgisCadastre) pour import des données MAJIC brutes
    """
    print(
        "Nettoyage base de données - Suppression tables métiers MAJIC - cf.QgisCadastre"
    )
    script_path = os.path.join(os.getcwd(), "temp/sql/commun_drop_metier.sql")
    conn = pg_connection()
    conn.execute_script(script_path)
    conn.close_connection()
    print("Base de données prête pour initialisation avec les tables métiers MAJIC.")


def init_db_for_majic_import():
    """
    Création des tables métiers (QgisCadastre) pour import des données MAJIC brutes
    """
    print("Initialisation base de données - tables métiers MAJIC - cf.QgisCadastre")
    script_path_create = os.path.join(os.getcwd(), "temp/sql/commun_create_metier.sql")
    script_pathNomenclature = os.path.join(
        os.getcwd(), "temp/sql/commun_insert_nomenclature.sql"
    )
    conn = pg_connection()
    conn.execute_script(script_path_create)
    conn.execute_script(script_pathNomenclature)
    conn.close_connection()
    print("Base de données initialisée avec les tables métiers MAJIC.")


def execute_format_majic_scripts():
    """
    Execute dans postgis les scripts de formatage des données MAJIC.
    Scripts QgisCadastre (import + formatage MAJIC dans tables métiers)
    + scripts KADATA (calculs indicateurs et croisements)
    """
    annee = "2019"
    lot = ""
    replace_dict = {"[ANNEE]": annee, "[LOT]": lot}

    print("Execution des scripts de formatage des données MAJIC")
    script_list = [
        "2019/majic3_formatage_donnees.sql",
        "traitements/majic/0-renommage_tables.sql",
        "traitements/majic/1-traitement_qualification_proprietaires.sql",
        "traitements/majic/2-traitement_local_pev.sql",
        "traitements/majic/3-traitement_lots.sql",
        "traitements/majic/4-traitement_suf.sql",
    ]

    scripts_count = len(script_list)
    etape = 0
    sql_scripts_dir = os.path.join(os.getcwd(), "temp/sql/")
    conn = pg_connection()
    # conn.setSearchPath()
    for script in script_list:
        etape += 1
        print("Etape " + str(etape) + "/" + str(scripts_count) + " : " + script)
        script_path = os.path.join(sql_scripts_dir, script)
        replace_parameters_in_script(script_path, replace_dict)
        conn.execute_script(script_path)
    conn.close_connection()
    print("Formatage terminé.")
