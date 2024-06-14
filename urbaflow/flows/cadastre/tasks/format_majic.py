#!/usr/bin/python
import os

from utils.script_utils import replace_parameters_in_script
from utils.dbutils import pg_connection


def cleanWithDropDbForMajicImport():
    """
    Suppression des tables métiers (QgisCadastre) pour import des données MAJIC brutes
    """
    print('Nettoyage base de données - Suppression tables métiers MAJIC - cf.QgisCadastre')
    scriptPath = os.path.join(os.getcwd(), 'temp/sql/commun_drop_metier.sql')
    conn = pg_connection()
    conn.executeScript(scriptPath)
    conn.closeConnection()
    print('Base de données prête pour initialisation avec les tables métiers MAJIC.')

def initDbForMajicImport():
    """
    Création des tables métiers (QgisCadastre) pour import des données MAJIC brutes
    """
    print('Initialisation base de données - tables métiers MAJIC - cf.QgisCadastre')
    scriptPathCreate = os.path.join(os.getcwd(), 'temp/sql/commun_create_metier.sql')
    scriptPathNomenclature = os.path.join(os.getcwd(), 'temp/sql/commun_insert_nomenclature.sql')
    conn = pg_connection()
    conn.executeScript(scriptPathCreate)
    conn.executeScript(scriptPathNomenclature)
    conn.closeConnection()
    print('Base de données initialisée avec les tables métiers MAJIC.')

def executeFormatageMajicScripts():
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

    print("Execution des scripts de formatage des données MAJIC")
    scriptList = [
        '2019/majic3_formatage_donnees.sql',
        'traitements/majic/0-renommage_tables.sql',
        'traitements/majic/1-traitement_qualification_proprietaires.sql',
        'traitements/majic/2-traitement_local_pev.sql',
        'traitements/majic/3-traitement_lots.sql',
        'traitements/majic/4-traitement_suf.sql'
    ]

    nombreDeScripts = len(scriptList)
    etape = 0
    sqlScriptsDir = os.path.join(os.getcwd(), 'temp/sql/')
    conn = pg_connection()
    #conn.setSearchPath()
    for script in scriptList:
        etape +=1
        print("Etape "+str(etape)+"/"+str(nombreDeScripts) + " : " + script)
        scriptPath = os.path.join(sqlScriptsDir, script)
        replace_parameters_in_script(scriptPath, replaceDict)
        conn.executeScript(scriptPath)
    conn.closeConnection()
    print("Formatage terminé.")

