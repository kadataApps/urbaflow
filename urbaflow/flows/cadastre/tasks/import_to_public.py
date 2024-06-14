import os
import psycopg2

from utils.dbutils import pg_connection
from utils.config import db_schema
from .get_communes_majic import get_imported_communes_from_file


def create_parcellaire_france():
    """
    Importation des parcelles créées dans la table principale
    parcellaire_france du schema "public"
    """
    print("Création de la table parcellaire_france dans public")
    script_path_create = os.path.join(
        os.getcwd(), "temp/sql/commun_create_parcellaire.sql"
    )
    conn = pg_connection()
    conn.execute_script(script_path_create)
    conn.close_connection()
    print("La table parcellaire_france a été créée.")


def create_proprietaire_droit():
    """
    Importation des données de proprietaire dans la table proprietaire_droit
    du schema "public"
    """
    print("Création de la table proprietaire_droit dans public")
    script_path_create = os.path.join(
        os.getcwd(), "temp/sql/commun_create_proprietaire.sql"
    )
    conn = pg_connection()
    conn.execute_script(script_path_create)
    conn.close_connection()
    print("La table proprietaire_droit a été créée.")


def create_pb0010_local():
    """
    Importation des données de local dans la table pb0010_local
    du schema "public"
    """
    print("Création de la table pb0010_local dans public")
    script_path_create = os.path.join(os.getcwd(), "temp/sql/commun_create_local.sql")
    conn = pg_connection()
    conn.execute_script(script_path_create)
    conn.close_connection()
    print("La table proprietaire_droit a été créée.")


def create_bati_france():
    """
    Importation de la table bati créée à partir des données du cadastre
    dans la table principale bati_france du schema "public"
    """
    print("Création de la table bati_france dans public")
    script_path_create = os.path.join(os.getcwd(), "temp/sql/commun_create_bati.sql")
    conn = pg_connection()
    conn.execute_script(script_path_create)
    conn.close_connection()
    print("La table bati_france a été créée.")


def insert_parcelles_to_public(connexion):
    schema = db_schema()["schema"]
    importSql = """
    INSERT INTO public.parcellaire_france (
      geom, idparcelle_geom, code_insee, idpar, idprocpte, dcntpa, jdatat,
      libcom, dlibvoi, adressepar, nbat, jdatatan, jannatmin, jannatmax,
      jannatminh, jannatmaxh, dcntarti, dcntnaf, nlocal, spevtot, nloclog,
      nloccom, nloccomsec, nloccomter, nlogh, nloghvac, nloghpp, nloghlm, ncp,
      ndroit, descprop, ndroitpro, ndroitges, ndroitpro_parcelle_bati, typprop, typproppro, typpropges,
      ddenomprop, ddenomproppro, ddenompropges
      )
    SELECT
      geom, idparcelle_geom, code_insee, idpar, idprocpte, dcntpa, jdatat,
      libcom, dlibvoi, adressepar, nbat, jdatatan, jannatmin, jannatmax,
      jannatminh, jannatmaxh, dcntarti, dcntnaf, nlocal, spevtot, nloclog, nloccom, nloccomsec,
      nloccomter, nlogh, nloghvac, nloghpp, nloghlm, ncp, ndroit, descprop,
      ndroitpro, ndroitges, ndroitpro_parcelle_bati, typprop, typproppro, typpropges, ddenomprop,
      ddenomproppro, ddenompropges
    FROM """
    importSql += f"{schema}.parcellaire;"

    connexion.execute_sql(importSql)

    print("Table parcellaire importée dans parcellaire_france")


def insert_proprietaire_to_public(connexion):
    schema = db_schema()["schema"]
    importSql = """
    INSERT INTO public.proprietaire_droit (
      proprietaire, annee, idprodroit, idprocpte, idpersonne, idvoie, idcom,
      idcomtxt, ccodep, ccodir, ccocom, dnupro, comptecommunal, dnulp, ccocif,
      dnuper, ccodro, ccodrotxt, typedroit, ccodem, gdesip, gtoper, ccoqua,
      gnexcf, dtaucf, dnatpr, dnatprtxt, ccogrm, codgrm, ccogrmtxt, dsglpm,
      dforme, ddenom, gtyp3, gtyp4, gtyp5, gtyp6, dlign3, dlign4, dlign5,
      dlign6, ccopay, ccodep1a2, ccodira, ccocomadr, ccovoi, ccoriv, dnvoiri,
      dindic, ccopos, dnirpp, dqualp, dnomlp, dprnlp, jdatnss, dldnss, epxnee,
      dnomcp, dprncp, topcdi, oriard, fixard, datadr, topdec, datdec, dsiren,
      ccmm, topja, datja, anospi, cblpmo, gtodge, gpctf, gpctsb, jmodge,
      jandge, jantfc, jantbc, dformjur, dnomus, dprnus, lot, locprop,
      locproptxt, codnom
      )
    SELECT
      proprietaire, annee, idprodroit, idprocpte, idpersonne, idvoie, idcom,
      idcomtxt, ccodep, ccodir, ccocom, dnupro, comptecommunal, dnulp, ccocif,
      dnuper, ccodro, ccodrotxt, typedroit, ccodem, gdesip, gtoper, ccoqua,
      gnexcf, dtaucf, dnatpr, dnatprtxt, ccogrm, codgrm, ccogrmtxt, dsglpm,
      dforme, ddenom, gtyp3, gtyp4, gtyp5, gtyp6, dlign3, dlign4, dlign5,
      dlign6, ccopay, ccodep1a2, ccodira, ccocom_adr AS ccocomadr, ccovoi, ccoriv, dnvoiri,
      dindic, ccopos, dnirpp, dqualp, dnomlp, dprnlp, jdatnss, dldnss, epxnee,
      dnomcp, dprncp, topcdi, oriard, fixard, datadr, topdec, datdec, dsiren,
      ccmm, topja, datja, anospi, cblpmo, gtodge, gpctf, gpctsb, jmodge,
      jandge, jantfc, jantbc, dformjur, dnomus, dprnus, lot, locprop,
      locproptxt, codnom
    FROM """
    importSql += f"{schema}.proprietaire;"

    connexion.execute_sql(importSql)
    print("Table proprietaire importée dans proprietaire_droit")


def insert_local_to_public(connexion):
    schema = db_schema()["schema"]
    importSql = """
    INSERT INTO public.pb0010_local (
      local10, annee, idlocal, idbat, idpar, idprocpte, ccodep, ccodir, ccocom, invar,
      local00, ccopre, ccosec, dnupla, dnubat, parcelle, ccoriv, voie, ccovoi, dnvoiri,
      gpdl, dsrpar, dnupro, comptecommunal, jdatat, dnufnl, ccoeva, ccitlv, dteloc,
      gtauom, dcomrd, ccoplc, cconlc, dvltrt, ccoape, cc48lc, dloy48a, top48a,
      dnatlc, dnupas, gnexcf, dtaucf, cchpr, jannat, dnbniv, hlmsem, postel,
      dnatcg, jdatcgl, dnutbx, dvltla, janloc, ccsloc, fburx, gimtom, cbtabt,
      jdtabt, jrtabt, jacloc, cconac, toprev, ccoifp, lot
      )
    SELECT
      local10, annee, idlocal, idbat, idpar, idprocpte, ccodep, ccodir, ccocom, invar,
      local00, ccopre, ccosec, dnupla, dnubat, parcelle, ccoriv, voie, ccovoi, dnvoiri,
      gpdl, dsrpar, dnupro, comptecommunal, jdatat, dnufnl, ccoeva, ccitlv, dteloc,
      gtauom, dcomrd, ccoplc, cconlc, dvltrt, ccoape, cc48lc, dloy48a, top48a,
      dnatlc, dnupas, gnexcf, dtaucf, cchpr, jannat, dnbniv, hlmsem, postel,
      dnatcg, jdatcgl, dnutbx, dvltla, janloc, ccsloc, fburx, gimtom, cbtabt,
      jdtabt, jrtabt, jacloc, cconac, toprev, ccoifp, lot
    FROM """
    importSql += f"{schema}.local10;"

    connexion.execute_sql(importSql)
    print("Table local10 importée dans pb0010_local")


def insert_bati_to_public(connexion):
    schema = db_schema()["schema"]

    importSql = (
        "INSERT INTO public.bati_france "
        "(wkb_geometry, type, nom, code_insee, created, updated ) "
        "SELECT wkb_geometry, type, nom, commune, created, updated "
        "FROM %(schema)s.cadastre_bati;" % {"schema": schema}
    )

    connexion.execute_sql(importSql)

    print("Table bati importée dans bati_france")


def delete_from_public(codes_insee, tableName, connexion):
    print(codes_insee)
    deleteSql = "DELETE FROM public.%s WHERE code_insee = ANY(ARRAY%s);" % (
        tableName,
        codes_insee,
    )

    connexion.execute_sql(deleteSql)

    print(
        "Les élémens de la table %s ont été supprimés pour les communes %s;"
        % (tableName, codes_insee)
    )


def check_if_table_exists(tableName, schema):
    tableDoesExistsSql = (
        "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname = '%s' and tablename='%s');"
        % (schema, tableName)
    )
    conn = pg_connection()
    conn.execute_sql(tableDoesExistsSql)
    tableDoesExists = conn.cur.fetchone()[0]
    return tableDoesExists


def flow_import_parcelles():
    config = get_imported_communes_from_file()
    # codes_insee = ast.literal_eval(config["communes"])
    codes_insee = config["communes"]
    tableName = "parcellaire_france"
    tableDoesExists = check_if_table_exists(tableName, schema="public")
    if not tableDoesExists:
        create_parcellaire_france()
    try:
        conn = pg_connection()
        delete_from_public(codes_insee, tableName, connexion=conn)
        insert_parcelles_to_public(connexion=conn)
        conn.commit()
    except psycopg2.DatabaseError as error:
        print(error)
    finally:
        if conn is not None:
            conn.close_connection()


def flow_import_proprietaire():
    tableName = "proprietaire_droit"
    tableDoesExists = check_if_table_exists(tableName, schema="public")
    if not tableDoesExists:
        create_proprietaire_droit()
    try:
        conn = pg_connection()
        insert_proprietaire_to_public(connexion=conn)
        conn.commit()
    except psycopg2.DatabaseError as error:
        print(error)
    finally:
        if conn is not None:
            conn.close_connection()


def flow_import_local():
    tableName = "pb0010_local"
    tableDoesExists = check_if_table_exists(tableName, schema="public")
    if not tableDoesExists:
        create_pb0010_local()
    try:
        conn = pg_connection()
        insert_local_to_public(connexion=conn)
        conn.commit()
    except psycopg2.DatabaseError as error:
        print(error)
    finally:
        if conn is not None:
            conn.close_connection()


def flow_import_bati():
    config = get_imported_communes_from_file()
    codes_insee = config["communes"]
    tableName = "bati_france"
    tableDoesExists = check_if_table_exists(tableName, schema="public")
    if tableDoesExists is not True:
        create_bati_france()
    try:
        conn = pg_connection()
        delete_from_public(codes_insee, tableName, connexion=conn)
        insert_bati_to_public(connexion=conn)
        conn.commit()
    except psycopg2.DatabaseError as error:
        print(error)
    finally:
        if conn is not None:
            conn.close_connection()
