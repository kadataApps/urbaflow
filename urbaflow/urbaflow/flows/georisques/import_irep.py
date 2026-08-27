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

# Registre National des Émissions Polluantes (IREP)
# URL par défaut (dernier millésime disponible 2024) : https://files.georisques.fr/irep/2024.zip

logger = get_logger(__name__)


@task
def create_table_irep(
    schema: str = "public", table_name: str = "risques_irep", recreate: bool = True
):
    """
    Crée la table PostGIS pour les données IREP (Registre des Émissions Polluantes).
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
                    identifiant text PRIMARY KEY,
                    nom_etablissement text,
                    numero_siret text,
                    adresse text,
                    code_postal text,
                    code_insee text,
                    commune text,
                    code_departement text,
                    departement text,
                    code_region text,
                    region text,
                    code_ape text,
                    libelle_ape text,
                    code_eprtr text,
                    libelle_eprtr text,
                    coordonnees_x numeric,
                    coordonnees_y numeric,
                    annee integer,
                    nb_emissions_air integer,
                    nb_emissions_eau integer,
                    nb_emissions_sol integer,
                    polluants_emis text,
                    total_prelevements_m3 numeric,
                    total_rejets_m3 numeric,
                    quantite_prod_dechets_non_dangereux_t numeric,
                    quantite_prod_dechets_dangereux_t numeric,
                    quantite_trait_dechets_non_dangereux_t numeric,
                    quantite_trait_dechets_dangereux_t numeric,
                    url_fiche text
                )
                """
            )
        )
        logger.info(
            "Table %s.%s créée si elle n'existait pas auparavant", schema, table_name
        )


@task
def consolidate_irep_data(dir_path: Path, year: int = 2024) -> pd.DataFrame:
    """
    Charge et agrège les tables IREP (etablissements, emissions,
    prelevements, rejets, dechets) pour produire une table synthétique.
    """
    csv_files = {}
    files = list_files_at_path(dir_path, r".*", extension=".csv")
    for file in files:
        base_name = os.path.basename(file).lower()
        encode_to_utf8(file)
        # Détection du séparateur
        with open(file, encoding="utf-8") as fp:
            line = fp.readline()
        sep = ";" if ";" in line else ","
        csv_files[base_name] = pd.read_csv(
            file, sep=sep, encoding="utf-8", low_memory=False
        )

    df_etab = csv_files.get("etablissements.csv")
    if df_etab is None:
        raise ValueError(
            "Le fichier etablissements.csv est introuvable dans le dossier IREP."
        )

    # Nettoyage et conversion de la clé d'identifiant
    df_etab["identifiant"] = df_etab["identifiant"].astype(str)
    df_etab = df_etab.drop_duplicates(subset=["identifiant"])

    # 1. Émissions (Air, Eau, Sol, polluants)
    df_em = csv_files.get("emissions.csv")
    if df_em is not None and not df_em.empty:
        df_em["identifiant"] = df_em["identifiant"].astype(str)
        em_air = (
            df_em[df_em["milieu"] == "Air"]
            .groupby("identifiant")["quantite"]
            .count()
            .astype(int)
            .rename("nb_emissions_air")
        )
        em_eau = (
            df_em[df_em["milieu"].astype(str).str.startswith("Eau", na=False)]
            .groupby("identifiant")["quantite"]
            .count()
            .astype(int)
            .rename("nb_emissions_eau")
        )
        em_sol = (
            df_em[df_em["milieu"] == "Sol"]
            .groupby("identifiant")["quantite"]
            .count()
            .astype(int)
            .rename("nb_emissions_sol")
        )
        em_polluants = (
            df_em.groupby("identifiant")["polluant"]
            .apply(lambda s: ", ".join(dict.fromkeys(s.dropna().astype(str))))
            .rename("polluants_emis")
        )
    else:
        em_air = pd.Series(name="nb_emissions_air", dtype="int64")
        em_eau = pd.Series(name="nb_emissions_eau", dtype="int64")
        em_sol = pd.Series(name="nb_emissions_sol", dtype="int64")
        em_polluants = pd.Series(name="polluants_emis", dtype="object")

    # 2. Prélèvements d'eau
    df_prel = csv_files.get("prelevements.csv")
    if df_prel is not None and not df_prel.empty:
        df_prel["identifiant"] = df_prel["identifiant"].astype(str)
        prel_cols = [
            c
            for c in [
                "prelevements_eaux_souterraines",
                "prelevements_eaux_surface",
                "prelevements_reseau_distribution",
                "prelevements_mer",
            ]
            if c in df_prel.columns
        ]
        prel_tot = (
            df_prel.groupby("identifiant")[prel_cols]
            .sum(numeric_only=True)
            .sum(axis=1)
            .rename("total_prelevements_m3")
        )
    else:
        prel_tot = pd.Series(name="total_prelevements_m3", dtype="float64")

    # 3. Rejets d'eau
    df_rej = csv_files.get("rejets.csv")
    if df_rej is not None and not df_rej.empty:
        df_rej["identifiant"] = df_rej["identifiant"].astype(str)
        rej_cols = [
            c
            for c in ["rejet_raccorde_m3_par_an", "rejet_isole_m3_par_an"]
            if c in df_rej.columns
        ]
        rej_tot = (
            df_rej.groupby("identifiant")[rej_cols]
            .sum(numeric_only=True)
            .sum(axis=1)
            .rename("total_rejets_m3")
        )
    else:
        rej_tot = pd.Series(name="total_rejets_m3", dtype="float64")

    # 4. Déchets (Production & Traitement)
    df_pdnd = csv_files.get("prod_dechets_non_dangereux.csv")
    if df_pdnd is not None and not df_pdnd.empty:
        df_pdnd["identifiant"] = df_pdnd["identifiant"].astype(str)
        pdnd_tot = (
            df_pdnd.groupby("identifiant")["quantite"]
            .sum(numeric_only=True)
            .rename("quantite_prod_dechets_non_dangereux_t")
        )
    else:
        pdnd_tot = pd.Series(
            name="quantite_prod_dechets_non_dangereux_t", dtype="float64"
        )

    df_pdd = csv_files.get("prod_dechets_dangereux.csv")
    if df_pdd is not None and not df_pdd.empty:
        df_pdd["identifiant"] = df_pdd["identifiant"].astype(str)
        pdd_tot = (
            df_pdd.groupby("identifiant")["quantite"]
            .sum(numeric_only=True)
            .rename("quantite_prod_dechets_dangereux_t")
        )
    else:
        pdd_tot = pd.Series(
            name="quantite_prod_dechets_dangereux_t", dtype="float64"
        )

    df_tdnd = csv_files.get("trait_dechets_non_dangereux.csv")
    if df_tdnd is not None and not df_tdnd.empty:
        df_tdnd["identifiant"] = df_tdnd["identifiant"].astype(str)
        tdnd_tot = (
            df_tdnd.groupby("identifiant")["quantite_traitee"]
            .sum(numeric_only=True)
            .rename("quantite_trait_dechets_non_dangereux_t")
        )
    else:
        tdnd_tot = pd.Series(
            name="quantite_trait_dechets_non_dangereux_t", dtype="float64"
        )

    df_tdd = csv_files.get("trait_dechets_dangereux.csv")
    if df_tdd is not None and not df_tdd.empty:
        df_tdd["identifiant"] = df_tdd["identifiant"].astype(str)
        tdd_tot = (
            df_tdd.groupby("identifiant")["quantite_traitee"]
            .sum(numeric_only=True)
            .rename("quantite_trait_dechets_dangereux_t")
        )
    else:
        tdd_tot = pd.Series(
            name="quantite_trait_dechets_dangereux_t", dtype="float64"
        )

    # Fusion sur l'établissement
    merged = (
        df_etab.merge(em_air, on="identifiant", how="left")
        .merge(em_eau, on="identifiant", how="left")
        .merge(em_sol, on="identifiant", how="left")
        .merge(em_polluants, on="identifiant", how="left")
        .merge(prel_tot, on="identifiant", how="left")
        .merge(rej_tot, on="identifiant", how="left")
        .merge(pdnd_tot, on="identifiant", how="left")
        .merge(pdd_tot, on="identifiant", how="left")
        .merge(tdnd_tot, on="identifiant", how="left")
        .merge(tdd_tot, on="identifiant", how="left")
    )

    merged["annee"] = int(year)
    merged["url_fiche"] = merged["identifiant"].apply(
        lambda id_val: f"https://www.georisques.gouv.fr/dossiers/irep/donnees/etablissement/{id_val}/donnees"
    )

    int_cols = ["annee", "nb_emissions_air", "nb_emissions_eau", "nb_emissions_sol"]
    for col in int_cols:
        if col in merged.columns:
            merged[col] = (
                merged[col].fillna(0).astype(float).astype(int)
            )

    # Nettoyage des colonnes attendues
    expected_cols = [
        "identifiant",
        "nom_etablissement",
        "numero_siret",
        "adresse",
        "code_postal",
        "code_insee",
        "commune",
        "code_departement",
        "departement",
        "code_region",
        "region",
        "code_ape",
        "libelle_ape",
        "code_eprtr",
        "libelle_eprtr",
        "coordonnees_x",
        "coordonnees_y",
        "annee",
        "nb_emissions_air",
        "nb_emissions_eau",
        "nb_emissions_sol",
        "polluants_emis",
        "total_prelevements_m3",
        "total_rejets_m3",
        "quantite_prod_dechets_non_dangereux_t",
        "quantite_prod_dechets_dangereux_t",
        "quantite_trait_dechets_non_dangereux_t",
        "quantite_trait_dechets_dangereux_t",
        "url_fiche",
    ]
    available_cols = [c for c in expected_cols if c in merged.columns]
    return merged[available_cols]


@task
def load_irep(
    df: pd.DataFrame, schema: str = "public", table_name: str = "risques_irep"
):
    """
    Charge les données IREP dans PostGIS.
    """
    if df.empty:
        logger.info("Aucune donnée IREP à insérer.")
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


@task
def add_geometry_column_to_table(
    schema: str = "public", table_name: str = "risques_irep"
):
    """
    Ajoute la colonne de géométrie PostGIS geom et l'index GIST.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                ALTER TABLE {q(schema)}.{q(table_name)} 
                    ADD COLUMN IF NOT EXISTS 
                    geom geometry(POINT, 2154);
                CREATE INDEX IF NOT EXISTS {q(f"sidx_{table_name}_geom")}
                    ON {q(schema)}.{q(table_name)} USING GIST (geom);
                """
            )
        )


@task
def populate_geom(schema: str = "public", table_name: str = "risques_irep"):
    """
    Calcule la géométrie Lambert 93 (EPSG:2154) à partir des coordonnées WGS84.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                UPDATE {q(schema)}.{q(table_name)}
                SET geom = ST_Transform(
                    ST_SetSRID(ST_MakePoint(coordonnees_x, coordonnees_y), 4326),
                    2154
                )
                WHERE coordonnees_x IS NOT NULL AND coordonnees_y IS NOT NULL;
                """
            )
        )


@flow
def import_risques_irep_flow(
    dirname: Path | None = None,
    year: int = 2024,
    db_schema: str = "public",
    table_name: str = "risques_irep",
    recreate: bool = False,
):
    """
    Flow d'importation du Registre National des Émissions Polluantes (IREP).
    Si le répertoire n'est pas fourni, l'archive ZIP du millésime est téléchargée.

    Exemple d'URL : https://files.georisques.fr/irep/2024.zip
    """
    create_table_irep(schema=db_schema, table_name=table_name, recreate=recreate)
    add_geometry_column_to_table(schema=db_schema, table_name=table_name)

    if dirname is None:
        logger.info("Téléchargement des données IREP pour le millésime %d", year)
        url = f"https://files.georisques.fr/irep/{year}.zip"
        target_dir = TEMP_DIR / "georisques/irep" / str(year)
        target_dir.mkdir(parents=True, exist_ok=True)

        download_and_unzip(url, extract_to_path=target_dir)
        dirname = target_dir

    logger.info("Consolidation et agrégation des tables IREP depuis %s", dirname)
    df_consolidated = consolidate_irep_data(dirname, year=year)

    logger.info("Chargement dans la table PostGIS %s.%s", db_schema, table_name)
    load_irep(df_consolidated, schema=db_schema, table_name=table_name)

    populate_geom(schema=db_schema, table_name=table_name)
