
import os

from utils.dbutils import pg_connection


def executeInitCadastre():
    """
    Création table cadastre_parcelles pour import du cadastre
    (Si la table n'existe pas)
    """
    print('Création table cadastre_parcelles')
    scriptPathCreate = os.path.join(
        os.getcwd(), 'temp/sql/traitements/cadastre/0-initialisation_cadastre_parcelle.sql')
    conn = pg_connection()
    conn.executeScript(scriptPathCreate)
    conn.closeConnection()
    print('La table cadastre_parcelles a été créée si nécessaire.')


def executeFormatageCadastre():
    """
    Ajout et mise à jour colonne geo_parcelles 
    sur cadastre_parcelles pour jointure
    avec MAJIC
    """
    print('Ajout/Mise à jour geo_parcelles sur table cadastre_parcelles')
    scriptPathCreate = os.path.join(
        os.getcwd(), 'temp/sql/traitements/cadastre/1-traitement_cadastre_parcelles.sql')
    conn = pg_connection()
    conn.executeScript(scriptPathCreate)
    conn.closeConnection()
    print('Table cadastre_parcelles mise à jour.')


def executeInitBati():
    """
    Création table cadastre_bati pour import du cadastre
    (Si la table n'existe pas)
    """
    print('Création table cadastre_bati')
    scriptPathCreate = os.path.join(
        os.getcwd(), 'temp/sql/traitements/bati/0-initialisation_cadastre_bati.sql')
    conn = pg_connection()
    conn.executeScript(scriptPathCreate)
    conn.closeConnection()
    print('La table cadastre_bati a été créée si nécessaire.')
