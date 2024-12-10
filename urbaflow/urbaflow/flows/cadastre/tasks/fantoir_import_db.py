import os

from urbaflow.urbaflow.shared_tasks.db_engine import create_engine
from urbaflow.urbaflow.shared_tasks.db_sql_utils import run_sql_script
from urbaflow.urbaflow.shared_tasks.sql_query_utils import replace_parameters_in_script


def create_fantoir():
    """
    Création des tables métiers (QgisCadastre) pour import des données  FANTOIR / MAJIC brutes
    """
    print(
        "Initialisation base de données - tables métiers FANTOIR / MAJIC - cf.QgisCadastre"
    )
    script_path_create = os.path.join(os.getcwd(), "temp/sql/create_fantoir.sql")
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
    print("Base de données initialisée avec les tables métiers FANTOIR/MAJIC.")


def truncate_fantoir_tables():
    """
    Vide les tables communes et voies avant l'import/formatage avec formatage_fantoir
    """
    sql = "TRUNCATE TABLE voie_france; TRUNCATE TABLE commune_france;"
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=sql, connection=conn)


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

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path, connection=conn)
    print("Formatage terminé.")
