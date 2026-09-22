import os
from pathlib import Path

import pandas as pd
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_file_utils import download_and_unzip
from shared_tasks.etl_gpd_utils import load
from shared_tasks.file_utils import encode_to_utf8, list_files_at_path
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL

# Données GASPAR (Gestion Assistée des Procédures Administratives relatives aux Risques)
# URL nationale : https://files.georisques.fr/GASPAR/gaspar.zip

logger = get_logger(__name__)


@task
def create_table_gaspar(
    schema: str = "public", table_name: str = "risques_gaspar", recreate: bool = True
):
    """
    Crée la table PostGIS pour les procédures administratives relatives aux risques.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {q(schema)}.{q(table_name)}"))
            logger.info(
                "Suppression de la table %s.%s si elle existe", schema, table_name
            )

        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {q(schema)}.{q(table_name)} (
                    id text PRIMARY KEY,
                    code_insee text,
                    nom_commune text,
                    code_procedure text,
                    type_procedure text,
                    nom_procedure text,
                    risques text,
                    statut text,
                    date_procedure date
                )
                """
            )
        )
        logger.info(
            "Table %s.%s créée si elle n'existait pas auparavant", schema, table_name
        )


@task
def consolidate_gaspar_data(dir_path: Path) -> pd.DataFrame:
    """
    Consolide l'ensemble des fichiers CSV GASPAR (PPRN, PPRM, PPRT, CatNat, AZI, etc.)
    en une table unique récapitulant les procédures administratives par commune.
    """
    csv_files = {}
    files = list_files_at_path(dir_path, r".*", extension=".csv")
    for file in files:
        base_name = os.path.basename(file).lower()
        encode_to_utf8(file)
        with open(file, encoding="utf-8") as fp:
            line = fp.readline()
        sep = ";" if ";" in line else ","
        csv_files[base_name] = pd.read_csv(
            file, sep=sep, encoding="utf-8", low_memory=False
        )

    records = []

    # 1. PPR (PPRN, PPRM, PPRT)
    ppr_mapping = [
        ("pprn", "PPRN"),
        ("pprm", "PPRM"),
        ("pprt", "PPRT"),
    ]
    for key_prefix, ppr_type in ppr_mapping:
        matched_file = next(
            (fname for fname in csv_files if fname.startswith(key_prefix)), None
        )
        if matched_file is None:
            continue
        df_ppr = csv_files[matched_file]
        for _, row in df_ppr.iterrows():
            c_insee = str(row.get("CODE INSEE COMMUNE") or "").strip()
            if c_insee and c_insee.lower() != "nan":
                c_insee = c_insee.zfill(5)
            else:
                c_insee = None

            c_proc = str(row.get("CODE PROCEDURE") or "").strip() or None

            r1 = str(row.get("LIBELLE RISQUE 1") or "").strip()
            r2 = str(row.get("LIBELLE RISQUE 2") or "").strip()
            r3 = str(row.get("LIBELLE RISQUE 3") or "").strip()
            risques_list = [
                r for r in [r1, r2, r3] if r and r.lower() != "nan" and r != "None"
            ]
            risques = ", ".join(dict.fromkeys(risques_list)) or None

            nom_proc = (
                str(
                    row.get("LIBELLE PROCEDURE") or row.get("LIBELLE MODELE") or ""
                ).strip()
                or None
            )
            statut = (
                str(
                    row.get("LIBELLE ETAT") or row.get("LIBELLE SOUS-ETAT") or ""
                ).strip()
                or None
            )

            d_proc = (
                str(
                    row.get("DATE ETAT")
                    or row.get("APPROBATION")
                    or row.get("PRESCRIPTION")
                    or ""
                ).strip()[:10]
                or None
            )
            if d_proc and (d_proc.lower() == "nan" or len(d_proc) < 8):
                d_proc = None

            records.append(
                {
                    "code_insee": c_insee,
                    "nom_commune": row.get("NOM COMMUNE"),
                    "code_procedure": c_proc,
                    "type_procedure": ppr_type,
                    "nom_procedure": nom_proc,
                    "risques": risques,
                    "statut": statut,
                    "date_procedure": d_proc,
                }
            )

    # 2. CatNat
    matched_catnat = next(
        (fname for fname in csv_files if fname.startswith("catnat")), None
    )
    if matched_catnat is not None:
        df_cat = csv_files[matched_catnat]
        for _, row in df_cat.iterrows():
            c_insee = str(row.get("code_commune") or "").strip()
            if c_insee and c_insee.lower() != "nan":
                c_insee = c_insee.zfill(5)
            else:
                c_insee = None

            c_proc = str(row.get("id_gaspar") or "").strip() or None
            r_label = str(row.get("lib_risque_jo") or "").strip() or None
            d_proc = (
                str(
                    row.get("date_publication_jo")
                    or row.get("date_signature_arrete")
                    or ""
                ).strip()[:10]
                or None
            )
            if d_proc and (d_proc.lower() == "nan" or len(d_proc) < 8):
                d_proc = None

            nom_catnat = f"Arrêté CatNat - {r_label}" if r_label else "Arrêté CatNat"
            records.append(
                {
                    "code_insee": c_insee,
                    "nom_commune": row.get("libelle_commune"),
                    "code_procedure": c_proc,
                    "type_procedure": "CATNAT",
                    "nom_procedure": nom_catnat,
                    "risques": r_label,
                    "statut": "Publié JO",
                    "date_procedure": d_proc,
                }
            )

    # 3. AZI (Atlas des Zones Inondables)
    matched_azi = next((fname for fname in csv_files if fname.startswith("azi")), None)
    if matched_azi is not None:
        df_azi = csv_files[matched_azi]
        for _, row in df_azi.iterrows():
            c_insee = str(row.get("cod_commune") or "").strip()
            if c_insee and c_insee.lower() != "nan":
                c_insee = c_insee.zfill(5)
            else:
                c_insee = None

            c_proc = str(row.get("id_gaspar") or "").strip() or None
            d_proc = (
                str(
                    row.get("dat_diffusion") or row.get("dat_program_deb") or ""
                ).strip()[:10]
                or None
            )
            if d_proc and (d_proc.lower() == "nan" or len(d_proc) < 8):
                d_proc = None

            records.append(
                {
                    "code_insee": c_insee,
                    "nom_commune": row.get("lib_commune"),
                    "code_procedure": c_proc,
                    "type_procedure": "AZI",
                    "nom_procedure": row.get("libelle"),
                    "risques": row.get("list_risques"),
                    "statut": "Diffusé",
                    "date_procedure": d_proc,
                }
            )

    # 4. DICRIM
    matched_dicrim = next(
        (fname for fname in csv_files if fname.startswith("dicrim")), None
    )
    if matched_dicrim is not None:
        df_dic = csv_files[matched_dicrim]
        for _, row in df_dic.iterrows():
            c_insee = str(row.get("cod_commune") or "").strip()
            if c_insee and c_insee.lower() != "nan":
                c_insee = c_insee.zfill(5)
            else:
                c_insee = None

            d_proc = str(row.get("dat_publi_dicrim") or "").strip()[:10] or None
            if d_proc and (d_proc.lower() == "nan" or len(d_proc) < 8):
                d_proc = None

            records.append(
                {
                    "code_insee": c_insee,
                    "nom_commune": row.get("lib_commune"),
                    "code_procedure": None,
                    "type_procedure": "DICRIM",
                    "nom_procedure": (
                        "Document d'Information Communal sur les Risques Majeurs"
                    ),
                    "risques": "Information préventive",
                    "statut": "Publié",
                    "date_procedure": d_proc,
                }
            )

    # 5. TIM (Transmission d'Information au Maire)
    matched_tim = next((fname for fname in csv_files if fname.startswith("tim")), None)
    if matched_tim is not None:
        df_tim = csv_files[matched_tim]
        for _, row in df_tim.iterrows():
            c_insee = str(row.get("code_commune") or "").strip()
            if c_insee and c_insee.lower() != "nan":
                c_insee = c_insee.zfill(5)
            else:
                c_insee = None

            d_proc = str(row.get("date_transmission") or "").strip()[:10] or None
            if d_proc and (
                d_proc.lower() == "nan" or len(d_proc) < 8 or d_proc.startswith("1900")
            ):
                d_proc = None

            records.append(
                {
                    "code_insee": c_insee,
                    "nom_commune": row.get("libelle_commune"),
                    "code_procedure": None,
                    "type_procedure": "TIM",
                    "nom_procedure": "Transmission d'Information au Maire",
                    "risques": "Information préventive",
                    "statut": "Transmis",
                    "date_procedure": d_proc,
                }
            )

    df_consolidated = pd.DataFrame(records)

    # Génération d'une clé primaire séquentielle unique pour la table
    df_consolidated["id"] = (df_consolidated.index + 1).astype(str)

    # Réordonnancement des colonnes
    cols = [
        "id",
        "code_insee",
        "nom_commune",
        "code_procedure",
        "type_procedure",
        "nom_procedure",
        "risques",
        "statut",
        "date_procedure",
    ]
    return df_consolidated[cols]


@task
def load_gaspar(
    df: pd.DataFrame, schema: str = "public", table_name: str = "risques_gaspar"
):
    """
    Charge les données consolidées des procédures GASPAR dans la base de données.
    """
    if df.empty:
        logger.info("Aucune donnée GASPAR à insérer.")
        return

    e = create_engine()
    with e.begin() as conn:
        load(
            df,
            connection=conn,
            table_name=table_name,
            how="append",
            schema=schema,
            logger=logger,
        )


@flow
def import_risques_gaspar_flow(
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "risques_gaspar",
    recreate: bool = False,
):
    """
    Flow d'importation des procédures administratives relatives aux risques (GASPAR).
    Si le répertoire n'est pas fourni, le fichier ZIP national est téléchargé.

    URL : https://files.georisques.fr/GASPAR/gaspar.zip
    """
    create_table_gaspar(schema=db_schema, table_name=table_name, recreate=recreate)

    if dirname is None:
        logger.info("Téléchargement de la base nationale GASPAR")
        url = "https://files.georisques.fr/GASPAR/gaspar.zip"
        target_dir = TEMP_DIR / "georisques/gaspar"
        target_dir.mkdir(parents=True, exist_ok=True)

        download_and_unzip(url, extract_to_path=target_dir)
        dirname = target_dir

    logger.info("Consolidation des procédures GASPAR depuis %s", dirname)
    df_consolidated = consolidate_gaspar_data(dirname)

    logger.info("Insertion des données dans la table %s.%s", db_schema, table_name)
    load_gaspar(df_consolidated, schema=db_schema, table_name=table_name)
