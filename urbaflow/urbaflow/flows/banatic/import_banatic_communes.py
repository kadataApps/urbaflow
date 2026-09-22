import urllib.request
from pathlib import Path

import pandas as pd
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import load
from shared_tasks.file_utils import encode_to_utf8
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL

# Données BANATIC
# Périmètre et liste des EPCI à fiscalité propre (EPCI FP)
URL_BANATIC_EPCI_FP = (
    "https://www.data.gouv.fr/api/1/datasets/r/6e05c448-62cc-4470-aa0f-4f31adea0bc4"
)
# Correspondance SIREN et code INSEE des communes
URL_BANATIC_COMMUNES_SIREN = (
    "https://www.data.gouv.fr/api/1/datasets/r/5d3cfdd0-00de-43fe-a5db-dffeacec6fc7"
)

logger = get_logger(__name__)


@task
def create_table_banatic_communes(
    schema: str = "public",
    table_name: str = "banatic_communes",
    recreate: bool = True,
):
    """
    Crée la table banatic_communes dans PostGIS.
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
                    code_insee text PRIMARY KEY,
                    siren_commune text,
                    nom_commune text,
                    code_departement text,
                    code_region text,
                    siren_epci text,
                    nom_epci text,
                    nature_juridique_epci text,
                    mode_financement_epci text,
                    nb_membres_epci integer,
                    total_pop_tot_epci integer,
                    total_pop_mun_epci integer,
                    pop_tot_commune integer,
                    pop_mun_commune integer
                )
                """
            )
        )
        logger.info(
            "Table %s.%s créée si elle n'existait pas auparavant", schema, table_name
        )


def clean_int_series(series: pd.Series) -> pd.Series:
    """
    Nettoie les espaces insecables et convertit une colonne en entier (nullable).
    """
    cleaned = (
        series.astype(str)
        .str.replace(r"\s+", "", regex=True)
        .str.replace("\xa0", "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


@task
def download_banatic_files() -> tuple[Path, Path]:
    """
    Télécharge les fichiers CSV BANATIC depuis data.gouv.fr.
    """
    target_dir = TEMP_DIR / "banatic"
    target_dir.mkdir(parents=True, exist_ok=True)

    epci_fp_file = target_dir / "epci_fp.csv"
    communes_siren_file = target_dir / "communes_siren.csv"

    logger.info("Téléchargement du fichier BANATIC EPCI FP...")
    content_epci = urllib.request.urlopen(URL_BANATIC_EPCI_FP).read()
    with open(epci_fp_file, "wb") as f:
        f.write(content_epci)

    logger.info("Téléchargement du fichier BANATIC Correspondance SIREN/INSEE...")
    content_insee = urllib.request.urlopen(URL_BANATIC_COMMUNES_SIREN).read()
    with open(communes_siren_file, "wb") as f:
        f.write(content_insee)

    encode_to_utf8(str(epci_fp_file))
    encode_to_utf8(str(communes_siren_file))

    return epci_fp_file, communes_siren_file


@task
def consolidate_banatic_communes(
    epci_fp_file: Path, communes_siren_file: Path
) -> pd.DataFrame:
    """
    Consolide les communes avec les informations relatives à l'EPCI FP.
    """
    logger.info("Lecture des fichiers BANATIC...")
    df_epci = pd.read_csv(
        epci_fp_file, sep=";", encoding="utf-8", dtype=str, low_memory=False
    )
    df_insee = pd.read_csv(
        communes_siren_file, sep=";", encoding="utf-8", dtype=str, low_memory=False
    )

    # Normalisation des colonnes de la correspondance SIREN / Code INSEE
    df_insee = df_insee.rename(
        columns={
            "Code INSEE de la commune": "code_insee",
            "Siren": "siren_commune",
            "Nom de la commune": "nom_commune",
        }
    )

    df_insee["code_insee"] = df_insee["code_insee"].astype(str).str.strip().str.zfill(5)
    df_insee["siren_commune"] = df_insee["siren_commune"].astype(str).str.strip()
    df_insee = df_insee.drop_duplicates(subset=["code_insee"])

    # Normalisation des colonnes EPCI FP
    df_epci["insee"] = df_epci["insee"].astype(str).str.strip().str.zfill(5)
    df_epci["siren"] = df_epci["siren"].astype(str).str.strip()
    df_epci = df_epci.drop_duplicates(subset=["insee"])

    # Fusion des données communes avec les données EPCI FP
    merged = df_insee.merge(df_epci, left_on="code_insee", right_on="insee", how="left")

    merged["code_departement"] = merged["dep_com"].fillna(merged["dept"])
    merged["code_region"] = merged["dept"].fillna("")

    merged = merged.rename(
        columns={
            "siren": "siren_epci",
            "raison_sociale": "nom_epci",
            "nature_juridique": "nature_juridique_epci",
            "mode_financ": "mode_financement_epci",
            "nb_membres": "nb_membres_epci",
            "total_pop_tot": "total_pop_tot_epci",
            "total_pop_mun": "total_pop_mun_epci",
            "ptot_2025": "pop_tot_commune",
            "pmun_2025": "pop_mun_commune",
        }
    )

    # Conversion propre des colonnes numériques
    int_cols = [
        "nb_membres_epci",
        "total_pop_tot_epci",
        "total_pop_mun_epci",
        "pop_tot_commune",
        "pop_mun_commune",
    ]
    for col in int_cols:
        if col in merged.columns:
            merged[col] = clean_int_series(merged[col])

    cols_order = [
        "code_insee",
        "siren_commune",
        "nom_commune",
        "code_departement",
        "code_region",
        "siren_epci",
        "nom_epci",
        "nature_juridique_epci",
        "mode_financement_epci",
        "nb_membres_epci",
        "total_pop_tot_epci",
        "total_pop_mun_epci",
        "pop_tot_commune",
        "pop_mun_commune",
    ]
    return merged[cols_order]


@task
def load_banatic_communes(
    df: pd.DataFrame, schema: str = "public", table_name: str = "banatic_communes"
):
    """
    Insère les données consolidées des communes BANATIC dans la base de données.
    """
    if df.empty:
        logger.info("Aucune donnée BANATIC à insérer.")
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
            nullable_integer_columns=[
                "nb_membres_epci",
                "total_pop_tot_epci",
                "total_pop_mun_epci",
                "pop_tot_commune",
                "pop_mun_commune",
            ],
        )


@flow
def import_banatic_communes_flow(
    epci_fp_file: Path | None = None,
    communes_siren_file: Path | None = None,
    db_schema: str = "public",
    table_name: str = "banatic_communes",
    recreate: bool = True,
):
    """
    Flow d'importation de la table des communes BANATIC avec raccordement aux EPCI FP.
    Si les fichiers ne sont pas fournis, ils sont téléchargés automatiquement.
    """
    create_table_banatic_communes(
        schema=db_schema, table_name=table_name, recreate=recreate
    )

    if epci_fp_file is None or communes_siren_file is None:
        logger.info("Téléchargement des fichiers BANATIC depuis data.gouv.fr...")
        epci_fp_file, communes_siren_file = download_banatic_files()

    logger.info("Consolidation des données BANATIC communes & EPCI FP...")
    df_consolidated = consolidate_banatic_communes(epci_fp_file, communes_siren_file)

    logger.info("Chargement dans la table PostGIS %s.%s", db_schema, table_name)
    load_banatic_communes(df_consolidated, schema=db_schema, table_name=table_name)
