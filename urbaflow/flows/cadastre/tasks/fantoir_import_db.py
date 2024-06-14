
import os

from utils.script_utils import replace_parameters_in_script
from utils.dbutils import pg_connection


def create_fantoir():
    """
    Création des tables métiers (QgisCadastre) pour import des données  FANTOIR / MAJIC brutes
    """
    print('Initialisation base de données - tables métiers FANTOIR / MAJIC - cf.QgisCadastre')
    scriptPathCreate = os.path.join(os.getcwd(), 'temp/sql/create_fantoir.sql')
    conn = pg_connection()
    conn.setSearchPathToPublic()
    conn.executeScript(scriptPathCreate)
    conn.closeConnection()
    print('Base de données initialisée avec les tables métiers FANTOIR/MAJIC.')

def truncate_fantoir_tables():
    """
    Vide les tables communes et voies avant l'import/formatage avec formatage_fantoir
    """
    sql = 'TRUNCATE TABLE voie_france; TRUNCATE TABLE commune_france;'
    conn = pg_connection()
    conn.setSearchPathToPublic()
    conn.executeSql(sql)
    conn.commit()
    conn.closeConnection()

def formatage_fantoir():
    """
    Execute dans postgis les scripts de formatage des données MAJIC.
    Scripts QgisCadastre (import + formatage MAJIC dans tables métiers)
    + scripts KADATA (calculs indicateurs et croisements)
    """
    annee = '2019'
    lot = ''
    replaceDict = {
        '[ANNEE]': annee,
        '[LOT]': lot
    }
    
    scriptPath = os.path.join(os.getcwd(), 'temp/sql/formatage_fantoir.sql')
    print("formatage Script Fantoir")
    replace_parameters_in_script(scriptPath, replaceDict)
    print("Script file: %s" % scriptPath)

    conn = pg_connection()
    conn.executeScript(scriptPath)
    conn.closeConnection()
    print("Formatage terminé.")

