"""
État des documents d'urbanisme d'un EPCI et de ses communes via l'API Docurba.

Documentation de l'API : https://docurba.beta.gouv.fr/dev/api
Endpoint utilisé : https://docurba.beta.gouv.fr/api/communes?departement={code}
"""

import io
from datetime import datetime, timezone

import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import load
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

logger = get_logger(__name__)

DOCURBA_API_URL = "https://docurba.beta.gouv.fr/api/communes"
DOCURBA_TIMEOUT_SECONDS = 180

TERRITORY_TYPE_COMMUNE = "COM"
TERRITORY_TYPE_EPCI = "EPCI"
RNU_LABEL = "RNU"
DISTINCT_VALUES_SEPARATOR = " / "

DOCUMENT_TYPE_LABELS = {
    "CC": "Carte communale",
}

OUTPUT_COLUMNS = [
    "type_territoire",
    "code_territoire",
    "nom_territoire",
    "siren_epci",
    "nom_epci",
    "nb_communes",
    "document_opposable",
    "type_document_opposable",
    "date_approbation",
    "date_executoire",
    "document_en_cours",
    "type_procedure_en_cours",
    "date_prescription_en_cours",
    "etat_docurba",
    "collectivite_porteuse",
    "repartition_documents_opposables",
    "pa_docurba_id",
    "pc_docurba_id",
    "date_mise_a_jour",
]

DATE_COLUMNS = ["date_approbation", "date_executoire", "date_prescription_en_cours"]


def is_blank(value) -> bool:
    """Indique si une valeur est absente (None, NaN ou chaîne vide)."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return bool(pd.isna(value))


def empty_to_none(value):
    """Convertit les chaînes vides et valeurs manquantes en None."""
    return None if is_blank(value) else value


def get_departement_from_insee(code_insee: str) -> str:
    """
    Déduit le code département d'un code INSEE de commune
    (3 caractères pour l'outre-mer, 2 sinon).
    """
    code_insee = str(code_insee).strip().zfill(5)
    return code_insee[:3] if code_insee.startswith("97") else code_insee[:2]


def label_document_type(document_type: str | None) -> str:
    """
    Retourne le libellé du type de document d'urbanisme opposable
    (RNU en l'absence de document opposable).
    """
    if is_blank(document_type):
        return RNU_LABEL
    return DOCUMENT_TYPE_LABELS.get(str(document_type), str(document_type))


def label_ongoing_document_type(document_type: str | None) -> str | None:
    """
    Retourne le libellé du type de document en cours d'élaboration,
    ou None s'il n'y en a pas.
    """
    return None if is_blank(document_type) else label_document_type(document_type)


def summarize_distinct(values: pd.Series) -> str | None:
    """
    Concatène les valeurs distinctes non vides, triées par ordre alphabétique.
    """
    distinct = sorted({str(value) for value in values if not is_blank(value)})
    return DISTINCT_VALUES_SEPARATOR.join(distinct) if distinct else None


@task
def extract_epci_communes(
    siren_epci: str,
    schema: str = "public",
    table_name: str = "banatic_communes",
) -> pd.DataFrame:
    """
    Extrait de la table BANATIC les communes membres de l'EPCI.
    """
    engine = create_engine()
    with engine.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        query = text(
            f"""
            SELECT code_insee, nom_commune, siren_epci, nom_epci
            FROM {q(schema)}.{q(table_name)}
            WHERE siren_epci = :siren_epci
            ORDER BY code_insee
            """
        )
        df = pd.read_sql(query, conn, params={"siren_epci": str(siren_epci).strip()})

    if df.empty:
        raise ValueError(
            f"Aucune commune trouvée pour l'EPCI SIREN {siren_epci} dans "
            f"{schema}.{table_name}. Lancer d'abord la commande banatic-communes."
        )
    df["code_insee"] = df["code_insee"].astype(str).str.strip().str.zfill(5)
    logger.info(
        "%d commune(s) trouvée(s) pour l'EPCI %s (%s)",
        len(df),
        df["nom_epci"].iloc[0],
        siren_epci,
    )
    return df


@task(retries=2, retry_delay_seconds=10)
def fetch_docurba_communes(
    departement: str, before_date: str | None = None
) -> pd.DataFrame:
    """
    Télécharge le CSV Docurba des communes d'un département
    (plan opposable et plan en cours pour chaque commune).
    """
    params = {"departement": departement}
    if before_date:
        params["avant"] = before_date
    logger.info("Interrogation de l'API Docurba pour le département %s", departement)
    response = requests.get(
        DOCURBA_API_URL, params=params, timeout=DOCURBA_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    df = pd.read_csv(
        io.StringIO(response.content.decode("utf-8")),
        dtype=str,
        keep_default_na=False,
    )
    logger.info(
        "%d commune(s) reçue(s) de Docurba pour le département %s",
        len(df),
        departement,
    )
    return df


def build_commune_row(
    commune: pd.Series, plan: pd.Series | None, updated_at: datetime
) -> dict:
    """
    Construit la ligne d'une commune à partir de sa ligne Docurba
    (plan est None si la commune est absente de Docurba).
    """
    plan = plan if plan is not None else pd.Series(dtype=str)
    opposable_type = empty_to_none(plan.get("pa_type_document"))
    return {
        "type_territoire": TERRITORY_TYPE_COMMUNE,
        "code_territoire": commune["code_insee"],
        "nom_territoire": commune["nom_commune"],
        "siren_epci": commune["siren_epci"],
        "nom_epci": commune["nom_epci"],
        "nb_communes": 1,
        "document_opposable": None
        if plan.empty
        else label_document_type(opposable_type),
        "type_document_opposable": opposable_type,
        "date_approbation": empty_to_none(plan.get("pa_date_approbation")),
        "date_executoire": empty_to_none(plan.get("pa_date_executoire")),
        "document_en_cours": label_ongoing_document_type(plan.get("pc_type_document")),
        "type_procedure_en_cours": empty_to_none(plan.get("pc_type_procedure")),
        "date_prescription_en_cours": empty_to_none(plan.get("pc_date_prescription")),
        "etat_docurba": empty_to_none(plan.get("plan_libelle_code_etat_complet")),
        "collectivite_porteuse": empty_to_none(plan.get("cp_nom")),
        "repartition_documents_opposables": None,
        "pa_docurba_id": empty_to_none(plan.get("pa_docurba_id")),
        "pc_docurba_id": empty_to_none(plan.get("pc_docurba_id")),
        "date_mise_a_jour": updated_at,
    }


def build_commune_rows(
    df_communes: pd.DataFrame, df_docurba: pd.DataFrame, updated_at: datetime
) -> pd.DataFrame:
    """
    Construit une ligne par commune de l'EPCI à partir des données Docurba.
    """
    docurba_by_insee = df_docurba.drop_duplicates("code_insee").set_index("code_insee")
    missing = sorted(set(df_communes["code_insee"]) - set(docurba_by_insee.index))
    if missing:
        logger.warning(
            "%d commune(s) absente(s) de Docurba (COG différent ?) : %s",
            len(missing),
            ", ".join(missing),
        )

    rows = [
        build_commune_row(
            commune,
            docurba_by_insee.loc[commune["code_insee"]]
            if commune["code_insee"] in docurba_by_insee.index
            else None,
            updated_at,
        )
        for _, commune in df_communes.iterrows()
    ]
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def is_single_procedure(ids: pd.Series) -> bool:
    """Indique si une même procédure Docurba couvre toutes les communes."""
    return bool(ids.notna().all() and ids.nunique() == 1)


def build_epci_row(df_commune_rows: pd.DataFrame, updated_at: datetime) -> dict:
    """
    Construit la ligne de synthèse de l'EPCI à partir des lignes communales.

    - document opposable : celui couvrant toutes les communes s'il est unique
      (ex : PLUi), sinon la liste des types de documents distincts ;
    - dates : renseignées uniquement si une procédure unique couvre l'EPCI ;
    - document en cours : la liste des types de documents en cours distincts.
    """
    first = df_commune_rows.iloc[0]
    single_opposable = is_single_procedure(df_commune_rows["pa_docurba_id"])
    single_ongoing = is_single_procedure(df_commune_rows["pc_docurba_id"])

    def pick_or_summarize(column: str, is_single: bool):
        if is_single:
            return first[column]
        return summarize_distinct(df_commune_rows[column])

    def pick(column: str, is_single: bool):
        return first[column] if is_single else None

    distribution = (
        df_commune_rows["document_opposable"].dropna().value_counts().sort_index()
    )
    distribution_label = (
        ", ".join(f"{doc} : {count}" for doc, count in distribution.items()) or None
    )

    return {
        "type_territoire": TERRITORY_TYPE_EPCI,
        "code_territoire": first["siren_epci"],
        "nom_territoire": first["nom_epci"],
        "siren_epci": first["siren_epci"],
        "nom_epci": first["nom_epci"],
        "nb_communes": len(df_commune_rows),
        "document_opposable": pick_or_summarize("document_opposable", single_opposable),
        "type_document_opposable": pick_or_summarize(
            "type_document_opposable", single_opposable
        ),
        "date_approbation": pick("date_approbation", single_opposable),
        "date_executoire": pick("date_executoire", single_opposable),
        "document_en_cours": pick_or_summarize("document_en_cours", single_ongoing),
        "type_procedure_en_cours": pick_or_summarize(
            "type_procedure_en_cours", single_ongoing
        ),
        "date_prescription_en_cours": pick(
            "date_prescription_en_cours", single_ongoing
        ),
        "etat_docurba": None,
        "collectivite_porteuse": pick("collectivite_porteuse", single_opposable),
        "repartition_documents_opposables": distribution_label,
        "pa_docurba_id": pick("pa_docurba_id", single_opposable),
        "pc_docurba_id": pick("pc_docurba_id", single_ongoing),
        "date_mise_a_jour": updated_at,
    }


def build_documents_urbanisme(
    df_communes: pd.DataFrame,
    df_docurba: pd.DataFrame,
    updated_at: datetime | None = None,
) -> pd.DataFrame:
    """
    Construit le tableau final : une ligne pour l'EPCI puis une ligne par commune.
    """
    updated_at = updated_at or datetime.now(timezone.utc)
    df_commune_rows = build_commune_rows(df_communes, df_docurba, updated_at)
    epci_row = build_epci_row(df_commune_rows, updated_at)
    df = pd.concat(
        [pd.DataFrame([epci_row], columns=OUTPUT_COLUMNS), df_commune_rows],
        ignore_index=True,
    )
    for column in DATE_COLUMNS:
        dates = pd.to_datetime(df[column], errors="coerce", format="ISO8601")
        df[column] = [value.date() if pd.notna(value) else None for value in dates]
    df["nb_communes"] = df["nb_communes"].astype("Int64")
    return df


@task
def create_documents_table(schema: str, table_name: str, recreate: bool = False):
    """
    Crée la table des documents d'urbanisme si elle n'existe pas.
    """
    engine = create_engine()
    with engine.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {q(schema)}.{q(table_name)}"))
            logger.info("Suppression de la table %s.%s", schema, table_name)
        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {q(schema)}.{q(table_name)} (
                    type_territoire text NOT NULL,
                    code_territoire text NOT NULL,
                    nom_territoire text,
                    siren_epci text,
                    nom_epci text,
                    nb_communes integer,
                    document_opposable text,
                    type_document_opposable text,
                    date_approbation date,
                    date_executoire date,
                    document_en_cours text,
                    type_procedure_en_cours text,
                    date_prescription_en_cours date,
                    etat_docurba text,
                    collectivite_porteuse text,
                    repartition_documents_opposables text,
                    pa_docurba_id text,
                    pc_docurba_id text,
                    date_mise_a_jour timestamptz,
                    PRIMARY KEY (type_territoire, code_territoire)
                )
                """
            )
        )
        conn.execute(
            DDL(
                f"COMMENT ON TABLE {q(schema)}.{q(table_name)} IS "
                "'État des documents d''urbanisme par commune et EPCI "
                "(source : API Docurba)'"
            )
        )
    logger.info("Table %s.%s prête", schema, table_name)


@task
def replace_epci_documents(
    df: pd.DataFrame, siren_epci: str, schema: str, table_name: str
):
    """
    Remplace, dans une même transaction, les lignes de l'EPCI et de ses communes
    par les nouvelles données.
    """
    engine = create_engine()
    with engine.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        deleted = conn.execute(
            text(
                f"""
                DELETE FROM {q(schema)}.{q(table_name)}
                WHERE siren_epci = :siren_epci
                   OR (type_territoire = :epci AND code_territoire = :siren_epci)
                   OR (type_territoire = :commune AND code_territoire = ANY(:codes))
                """
            ),
            {
                "siren_epci": siren_epci,
                "epci": TERRITORY_TYPE_EPCI,
                "commune": TERRITORY_TYPE_COMMUNE,
                "codes": df.loc[
                    df["type_territoire"] == TERRITORY_TYPE_COMMUNE, "code_territoire"
                ].tolist(),
            },
        ).rowcount
        logger.info("%d ligne(s) existante(s) supprimée(s)", deleted)
        load(
            df,
            connection=conn,
            table_name=table_name,
            schema=schema,
            logger=logger,
            how="append",
            nullable_integer_columns=["nb_communes"],
        )
    logger.info("%d ligne(s) insérée(s) dans %s.%s", len(df), schema, table_name)


@flow(name="Docurba - documents d'urbanisme d'un EPCI")
def import_docurba_documents_flow(
    siren_epci: str,
    db_schema: str = "public",
    table_name: str = "docurba_documents_urbanisme",
    banatic_table: str = "banatic_communes",
    before_date: str | None = None,
    recreate: bool = False,
) -> pd.DataFrame:
    """
    Crée ou met à jour la table de l'état des documents d'urbanisme
    pour un EPCI et ses communes.

    1. Lecture des communes membres de l'EPCI dans la table BANATIC.
    2. Téléchargement des données Docurba pour chaque département concerné.
    3. Construction d'une ligne par commune et d'une ligne de synthèse EPCI.
    4. Remplacement des lignes de l'EPCI dans la table cible.
    """
    siren_epci = str(siren_epci).strip()
    df_communes = extract_epci_communes(siren_epci, db_schema, banatic_table)

    departements = sorted(
        {get_departement_from_insee(code) for code in df_communes["code_insee"]}
    )
    df_docurba = pd.concat(
        [fetch_docurba_communes(dep, before_date) for dep in departements],
        ignore_index=True,
    )

    df_documents = build_documents_urbanisme(df_communes, df_docurba)
    create_documents_table(db_schema, table_name, recreate=recreate)
    replace_epci_documents(df_documents, siren_epci, db_schema, table_name)

    epci_row = df_documents.iloc[0]
    logger.info(
        "EPCI %s : document opposable = %s ; date d'approbation = %s ; en cours = %s",
        epci_row["nom_territoire"],
        epci_row["document_opposable"],
        epci_row["date_approbation"],
        epci_row["document_en_cours"],
    )
    return df_documents
