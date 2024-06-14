#!/usr/bin/python
import os

from utils.script_utils import replace_parameters_in_script
from utils.dbutils import pg_connection


def executeMergeCadastreMajicScripts():
    """
    Execute dans postgis les scripts permettant de
    fusionner les données MAJIC et cadastre dans une seule table
    """
    annee = '2019'
    lot = ''
    replaceDict = {
        '[ANNEE]': annee,
        '[LOT]': lot
    }

    print("Execution des scripts de fusion Cadastre x MAJIC")
    scriptList = [
        'traitements/merge/0-creation_table_parcellaire.sql',
        'traitements/merge/1-affectation_proprietaire.sql',
        'traitements/merge/2-affectation_local_pev.sql',
        'traitements/merge/3-affectation_adresses.sql',
        'traitements/merge/4-anonymisation.sql',
    ]

    nombreDeScripts = len(scriptList)
    etape = 0
    sqlScriptsDir = os.path.join(os.getcwd(), 'temp/sql/')
    conn = pg_connection()
    for script in scriptList:
        etape +=1
        print("Etape "+str(etape)+"/"+str(nombreDeScripts) + " : " + script)
        scriptPath = os.path.join(sqlScriptsDir, script)
        replace_parameters_in_script(scriptPath, replaceDict)
        conn.executeScript(scriptPath)
    conn.closeConnection()
    print("Fusion Cadastre x MAJIC terminée.")

