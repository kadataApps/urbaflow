import os

from utils.script_utils import replace_parameters_in_script
from utils.dbutils import pg_connection


def create_fantoir():
    """
    Création des tables métiers (QgisCadastre) pour import des données  FANTOIR / MAJIC brutes
    """
    print(
        "Initialisation base de données - tables métiers FANTOIR / MAJIC - cf.QgisCadastre"
    )
    script_path_create = os.path.join(os.getcwd(), "temp/sql/create_fantoir.sql")
    conn = pg_connection()
    conn.set_search_path_to_public()
    conn.execute_script(script_path_create)
    conn.close_connection()
    print("Base de données initialisée avec les tables métiers FANTOIR/MAJIC.")


def truncate_fantoir_tables():
    """
    Vide les tables communes et voies avant l'import/formatage avec formatage_fantoir
    """
    sql = "TRUNCATE TABLE voie_france; TRUNCATE TABLE commune_france;"
    conn = pg_connection()
    conn.set_search_path_to_public()
    conn.execute_sql(sql)
    conn.commit()
    conn.close_connection()


def formatage_fantoir():
    """
    Execute dans postgis les scripts de formatage des données MAJIC.
    Scripts QgisCadastre (import + formatage MAJIC dans tables métiers)
    + scripts KADATA (calculs indicateurs et croisements)
    """
    annee = "2019"
    lot = ""
    replace_dict = {"[ANNEE]": annee, "[LOT]": lot}

    script_path = os.path.join(os.getcwd(), "temp/sql/formatage_fantoir.sql")
    print("formatage Script Fantoir")
    replace_parameters_in_script(script_path, replace_dict)
    print("Script file: %s" % script_path)

    conn = pg_connection()
    conn.execute_script(script_path)
    conn.close_connection()
    print("Formatage terminé.")
