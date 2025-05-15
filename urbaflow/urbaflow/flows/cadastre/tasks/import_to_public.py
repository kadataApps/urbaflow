import psycopg2

from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import get_logger
from shared_tasks.config import TEMP_DIR, db_schema
from .get_communes_majic import get_imported_communes_from_postgres


def create_parcellaire_france():
    """
    Importation des parcelles créées dans la table principale
    parcellaire_france du schema "public"
    """
    logger = get_logger()
    logger.info("Création de la table parcellaire_france dans public")
    script_path_create = TEMP_DIR / "sql/commun_create_parcellaire.sql"

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
    logger.info("La table parcellaire_france a été créée.")


def create_proprietaire_droit():
    """
    Importation des données de proprietaire dans la table proprietaire_droit
    du schema "public"
    """
    logger = get_logger()
    logger.info("Création de la table proprietaire_droit dans public")
    script_path_create = TEMP_DIR / "sql/commun_create_proprietaire.sql"

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
    logger.info("La table proprietaire_droit a été créée.")


def create_pb0010_local():
    """
    Importation des données de local dans la table pb0010_local
    du schema "public"
    """
    logger = get_logger()
    logger.info("Création de la table pb0010_local dans public")
    script_path_create = TEMP_DIR / "sql/commun_create_local.sql"
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
    logger.info("La table pb0010_local a été créée.")


def create_bati_france():
    """
    Importation de la table bati créée à partir des données du cadastre
    dans la table principale bati_france du schema "public"
    """
    logger = get_logger()
    logger.info("Création de la table bati_france dans public")
    script_path_create = TEMP_DIR / "sql/commun_create_bati.sql"
    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql_filepath=script_path_create, connection=conn)
    logger.info("La table bati_france a été créée.")


def insert_parcelles_to_public():
    logger = get_logger()
    schema = db_schema()
    import_query = """
    INSERT INTO public.parcellaire_france (
      geom, idparcelle_geom, code_insee, idpar, idpar_simple, idprocpte, dcntpa, jdatat,
      libcom, dlibvoi, adressepar, nbat, jdatatan, jannatmin, jannatmax,
      jannatminh, jannatmaxh, dcntarti, dcntnaf, nlocal, spevtot, nloclog,
      nloccom, nloccomsec, nloccomter, nlogh, nloghvac, nloghpp, nloghlm, ncp,
      ndroit, descprop, ndroitpro, ndroitges, ndroitpro_parcelle_bati, typprop, typproppro, typpropges,
      catpro, catpro_niv2, presgdprop,
      ddenomprop, ddenomproppro, ddenompropges
      )
    SELECT
      geom, idparcelle_geom, code_insee, idpar, idpar_simple, idprocpte, dcntpa, jdatat,
      libcom, dlibvoi, adressepar, nbat, jdatatan, jannatmin, jannatmax,
      jannatminh, jannatmaxh, dcntarti, dcntnaf, nlocal, spevtot, nloclog,
      nloccom, nloccomsec, nloccomter, nlogh, nloghvac, nloghpp, nloghlm, ncp,
      ndroit, descprop, ndroitpro, ndroitges, ndroitpro_parcelle_bati, typprop, typproppro, typpropges,
      catpro, catpro_niv2, presgdprop,
      ddenomprop, ddenomproppro, ddenompropges
    FROM """
    import_query += f"{schema}.parcellaire;"

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=import_query, connection=conn)

    logger.info("Table parcellaire importée dans parcellaire_france")


def insert_proprietaire_to_public():
    logger = get_logger()
    schema = db_schema()
    import_query = """
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
      locproptxt, codnom, catpro, catpro_niv2, nlogh, nloghvac, nloghpp,
      nloghmeu, nloghloue, nloghautre, nloghnonh, nloghlm, gdprop
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
      locproptxt, codnom, catpro, catpro_niv2, nlogh, nloghvac, nloghpp,
      nloghmeu, nloghloue, nloghautre, nloghnonh, nloghlm, gdprop
    FROM """
    import_query += f"{schema}.proprietaire;"

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=import_query, connection=conn)
    logger.info("Table proprietaire importée dans proprietaire_droit")


def insert_local_to_public():
    logger = get_logger()
    schema = db_schema()
    import_query = """
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
    import_query += f"{schema}.local10;"

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=import_query, connection=conn)
    logger.info("Table local10 importée dans pb0010_local")


def insert_bati_to_public():
    logger = get_logger()
    schema = db_schema()

    import_query = (
        "INSERT INTO public.bati_france "
        "(wkb_geometry, type, nom, code_insee, created, updated ) "
        "SELECT wkb_geometry, type, nom, commune, created, updated "
        "FROM %(schema)s.cadastre_bati;" % {"schema": schema}
    )

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=import_query, connection=conn)

    logger.info("Table bati importée dans bati_france")


def delete_from_public(
    codes_insee,
    table_name,
):
    logger = get_logger()
    logger.info(codes_insee)
    delete_query = "DELETE FROM public.%s WHERE code_insee = ANY(ARRAY%s);" % (
        table_name,
        codes_insee,
    )

    e = create_engine()
    with e.begin() as conn:
        run_sql_script(sql=delete_query, connection=conn)

    logger.info(
        "Les élémens de la table %s ont été supprimés pour les communes %s;"
        % (table_name, codes_insee)
    )


def flow_import_parcelles():
    logger = get_logger()
    communes_imported_df = get_imported_communes_from_postgres()
    table_name = "parcellaire_france"
    create_parcellaire_france()
    code_insee_to_be_imported = communes_imported_df["code_insee"].to_list()
    try:
        delete_from_public(code_insee_to_be_imported, table_name)
        insert_parcelles_to_public()
    except psycopg2.DatabaseError as error:
        logger.error(error)


def flow_import_proprietaire():
    logger = get_logger()
    create_proprietaire_droit()
    try:
        insert_proprietaire_to_public()
    except psycopg2.DatabaseError as error:
        logger.error(error)


def flow_import_local():
    logger = get_logger()
    create_pb0010_local()
    try:
        insert_local_to_public()
    except psycopg2.DatabaseError as error:
        logger.error(error)


def flow_import_bati():
    logger = get_logger()
    communes_df = get_imported_communes_from_postgres()
    table_name = "bati_france"
    create_bati_france()
    communes = communes_df["commune"].to_list()
    try:
        delete_from_public(communes, table_name)
        insert_bati_to_public()
    except psycopg2.DatabaseError as error:
        logger.error(error)
