"""Géolocalisation des autorisations SITADEL par le parcellaire historique."""

import csv
import json
import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from prefect import flow
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine, quote_identifier
from shared_tasks.logging_config import get_logger
from sqlalchemy import Connection, text

from .download_sitadel import SITADEL_DATAFILES, download_sitadel_file

logger = get_logger(__name__)

DETAIL_FILENAMES = tuple(
    filename for filename in SITADEL_DATAFILES if filename.startswith("sitadel_detail_")
)
HISTORY_TABLE = "dgfip_parcelle_historique"
RESULT_TABLE = "sitadel_geolocalisation"
BATCH_SIZE = 5000


def normalize_parcel_reference(
    commune: str, section: str, number: str
) -> dict[str, str | None]:
    """Normalise une référence sans inventer le préfixe cadastral absent de SDES."""
    section = section.strip().upper()
    number = number.strip()
    valid = (
        re.fullmatch(r"(?:[0-9]{5}|2[AB][0-9]{3})", commune)
        and re.fullmatch(r"[A-Z]{1,2}|0[A-Z]", section)
        and re.fullmatch(r"[0-9]{1,4}", number)
        and int(number) > 0
    )
    return {
        "section": section.zfill(2) if valid else None,
        "numero": number.zfill(4) if valid else None,
    }


def iter_authorizations(source_file: Path) -> Iterator[dict]:
    """Lit un CSV détaillé en flux et conserve les données et références inconnues."""
    with source_file.open(encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file, delimiter=";")
        columns = reader.fieldnames or []
        identifier_columns = [
            column for column in ("NUM_DAU", "NUM_PA", "NUM_PD") if column in columns
        ]
        reference_indexes = [
            index
            for index in range(1, 26)
            if {f"SEC_CADASTRE{index}", f"NUM_CADASTRE{index}"} & set(columns)
        ]
        required_columns = {
            "COMM",
            "DATE_REELLE_AUTORISATION",
            *(f"SEC_CADASTRE{index}" for index in reference_indexes),
            *(f"NUM_CADASTRE{index}" for index in reference_indexes),
        }
        if (
            len(columns) != len(set(columns))
            or len(identifier_columns) != 1
            or not reference_indexes
            or not required_columns.issubset(columns)
        ):
            raise ValueError(f"En-tête du CSV SITADEL invalide : {source_file}.")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(
                    f"Ligne CSV SITADEL mal formée : {source_file}:{reader.line_num}."
                )
            identifier = row[identifier_columns[0]].strip()
            if not identifier:
                raise ValueError(
                    f"Identifiant SITADEL absent : {source_file}:{reader.line_num}."
                )
            date_text = row["DATE_REELLE_AUTORISATION"].strip()
            try:
                authorization_date = (
                    date.fromisoformat(date_text) if date_text else None
                )
            except ValueError as error:
                raise ValueError(
                    f"Date SITADEL invalide : {source_file}:{reader.line_num}."
                ) from error
            commune = row["COMM"].strip().upper()
            references = []
            seen = set()
            for index in reference_indexes:
                section = row[f"SEC_CADASTRE{index}"].strip().upper()
                number = row[f"NUM_CADASTRE{index}"].strip()
                if not section and not number:
                    continue
                reference = normalize_parcel_reference(commune, section, number)
                key = (
                    (reference["section"], reference["numero"])
                    if reference["section"] is not None
                    else (section, number)
                )
                if key not in seen:
                    references.append(reference)
                    seen.add(key)
            yield {
                "source_file": source_file.name,
                "source_line": reader.line_num,
                "authorization_id": identifier,
                "commune": commune,
                "authorization_date": authorization_date,
                "source_data": json.dumps(row, ensure_ascii=False),
                "parcel_references": json.dumps(references),
            }


def stage_authorizations(connection: Connection, source_file: Path) -> int:
    """Charge un fichier par lots dans la transaction, sans tout garder en mémoire."""
    statement = text(
        "INSERT INTO pg_temp.sitadel_source VALUES "
        "(:source_file, :source_line, :authorization_id, :commune, "
        ":authorization_date, CAST(:source_data AS jsonb), "
        "CAST(:parcel_references AS jsonb))"
    )
    batch = []
    count = 0
    for authorization in iter_authorizations(source_file):
        batch.append(authorization)
        if len(batch) == BATCH_SIZE:
            connection.execute(statement, batch)
            count += len(batch)
            batch = []
    if batch:
        connection.execute(statement, batch)
        count += len(batch)
    if not count:
        raise ValueError(f"Le CSV SITADEL est vide : {source_file}.")
    logger.info("%d autorisations SITADEL chargées depuis %s.", count, source_file)
    return count


def geolocation_query(target_table: str, history_table: str) -> str:
    """Construit le rapprochement temporel, en refusant les candidats ex æquo."""
    return f"""
        INSERT INTO {target_table}
        WITH parcel_references AS MATERIALIZED (
            SELECT source.source_file, source.source_line, source.commune,
                   source.authorization_date, reference.ordinality AS reference_index,
                   reference.value ->> 'section' AS section,
                   reference.value ->> 'numero' AS numero
            FROM pg_temp.sitadel_source AS source
            CROSS JOIN LATERAL jsonb_array_elements(source.parcel_references)
                WITH ORDINALITY AS reference(value, ordinality)
        ), requested AS (
            SELECT DISTINCT commune, section, numero, authorization_date
            FROM parcel_references
            WHERE section IS NOT NULL AND authorization_date IS NOT NULL
        ), candidates AS (
            SELECT requested.*, parcel.id, parcel.millesime_debut,
                   parcel.millesime_fin, parcel.geom,
                   parcel.periode @> requested.authorization_date AS in_period,
                   rank() OVER (
                       PARTITION BY requested.commune, requested.section,
                                    requested.numero, requested.authorization_date
                       ORDER BY
                           CASE WHEN parcel.periode @> requested.authorization_date
                                THEN 0 ELSE 1 END,
                           CASE
                               WHEN parcel.periode @> requested.authorization_date
                                   THEN 0
                               WHEN requested.authorization_date
                                    < parcel.millesime_debut
                                   THEN parcel.millesime_debut
                                        - requested.authorization_date
                               ELSE requested.authorization_date - parcel.millesime_fin
                           END
                   ) AS priority
            FROM requested
            JOIN {history_table} AS parcel
              ON parcel.commune = requested.commune
             AND lpad(upper(parcel.section), 2, '0') = requested.section
             AND lpad(parcel.numero, 4, '0') = requested.numero
        ), best AS MATERIALIZED (
            SELECT *, count(*) OVER (
                PARTITION BY commune, section, numero, authorization_date
            ) AS candidate_count
            FROM candidates WHERE priority = 1
        ), unique_matches AS (
            SELECT * FROM best WHERE candidate_count = 1
        ), ambiguities AS (
            SELECT DISTINCT commune, section, numero, authorization_date
            FROM best WHERE candidate_count > 1
        ), details AS (
            SELECT reference.*,
                   matched.id, matched.millesime_debut, matched.millesime_fin,
                   matched.geom,
                   CASE
                       WHEN reference.section IS NULL THEN 'reference_invalide'
                       WHEN reference.authorization_date IS NULL THEN 'date_absente'
                       WHEN ambiguous.commune IS NOT NULL THEN 'ambigu'
                       WHEN matched.id IS NULL THEN 'introuvable'
                       WHEN matched.in_period THEN 'periode'
                       ELSE 'plus_proche'
                   END AS method
            FROM parcel_references AS reference
            LEFT JOIN unique_matches AS matched
                USING (commune, section, numero, authorization_date)
            LEFT JOIN ambiguities AS ambiguous
                USING (commune, section, numero, authorization_date)
        ), summary AS (
            SELECT source_file, source_line,
                   count(*) AS reference_count, count(id) AS matched_count,
                   jsonb_agg(jsonb_build_object(
                       'section', section, 'numero', numero, 'parcel_id', id,
                       'millesime_debut', millesime_debut,
                       'millesime_fin', millesime_fin, 'method', method
                   ) ORDER BY reference_index) AS parcel_matches,
                   ST_Multi(ST_UnaryUnion(ST_Collect(geom))) AS geom
            FROM details GROUP BY source_file, source_line
        )
        SELECT source.source_file, source.source_line, source.authorization_id,
               source.commune, source.authorization_date, source.source_data,
               coalesce(summary.reference_count, 0), coalesce(summary.matched_count, 0),
               coalesce(summary.parcel_matches, '[]'::jsonb),
               CASE WHEN summary.reference_count IS NULL THEN 'sans_reference'
                    WHEN summary.matched_count = 0 THEN 'non_geolocalise'
                    WHEN summary.matched_count < summary.reference_count THEN 'partiel'
                    ELSE 'complet' END,
               summary.geom,
               ST_PointOnSurface(summary.geom),
               ST_X(ST_Transform(ST_PointOnSurface(summary.geom), 4326)),
               ST_Y(ST_Transform(ST_PointOnSurface(summary.geom), 4326))
        FROM pg_temp.sitadel_source AS source
        LEFT JOIN summary USING (source_file, source_line)
    """


@flow
def geolocate_sitadel_flow(
    source_file: Path | None = None,
    db_schema: str = "public",
    parcels_schema: str | None = None,
    table_name: str = RESULT_TABLE,
) -> dict[str, int]:
    """Géolocalise un CSV détaillé local ou les quatre exports SDES téléchargés.

    La date réelle d'autorisation prime. Hors période connue, la version la
    plus proche est utilisée uniquement si elle est unique, sans départager
    arbitrairement des préfixes cadastraux. Sans date, aucune parcelle n'est
    choisie. Le remplacement des seuls fichiers traités est transactionnel.
    """
    parcels_schema = db_schema if parcels_schema is None else parcels_schema
    if (db_schema, table_name) == (parcels_schema, HISTORY_TABLE):
        raise ValueError(
            "La table cible doit être distincte de l'historique cadastral."
        )
    target_table = f"{quote_identifier(db_schema)}.{quote_identifier(table_name)}"
    history_table = (
        f"{quote_identifier(parcels_schema)}.{quote_identifier(HISTORY_TABLE)}"
    )
    source_files = (
        [Path(source_file)]
        if source_file is not None
        else [
            download_sitadel_file(filename, TEMP_DIR / "sitadel")
            for filename in DETAIL_FILENAMES
        ]
    )
    engine = create_engine(schema=db_schema)
    try:
        with engine.begin() as connection:
            # Sérialise les relances concurrentes sur une même table de résultat.
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:target))"),
                {"target": f"{db_schema}.{table_name}.sitadel"},
            )
            connection.execute(
                text(
                    f"SELECT id, commune, section, numero, millesime_debut, "
                    f"millesime_fin, periode, geom FROM {history_table} LIMIT 0"
                )
            )
            connection.execute(
                text(
                    "CREATE TEMPORARY TABLE sitadel_source ("
                    "source_file text, source_line bigint, authorization_id text, "
                    "commune text, authorization_date date, source_data jsonb, "
                    "parcel_references jsonb, PRIMARY KEY (source_file, source_line)"
                    ") ON COMMIT DROP"
                )
            )
            for path in source_files:
                stage_authorizations(connection, path)
            connection.execute(text("ANALYZE pg_temp.sitadel_source"))
            connection.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {target_table} ("
                    "source_file text NOT NULL, source_line bigint NOT NULL, "
                    "authorization_id text NOT NULL, commune text NOT NULL, "
                    "authorization_date date, source_data jsonb NOT NULL, "
                    "reference_count integer NOT NULL, matched_count integer NOT NULL, "
                    "parcel_matches jsonb NOT NULL, geolocation_status text NOT NULL, "
                    "geom geometry(MultiPolygon, 2154), "
                    "location geometry(Point, 2154), longitude double precision, "
                    "latitude double precision, PRIMARY KEY (source_file, source_line))"
                )
            )
            connection.execute(
                text(
                    f"DELETE FROM {target_table} WHERE source_file IN "
                    "(SELECT DISTINCT source_file FROM pg_temp.sitadel_source)"
                )
            )
            connection.execute(text(geolocation_query(target_table, history_table)))
            for suffix, expression in (
                ("geom_idx", "USING gist (geom)"),
                ("authorization_idx", "(authorization_id)"),
                ("commune_idx", "(commune)"),
            ):
                index = quote_identifier(f"{table_name}_{suffix}")
                connection.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS {index} "
                        f"ON {target_table} {expression}"
                    )
                )
            connection.execute(
                text(
                    f"COMMENT ON TABLE {target_table} IS "
                    "'Autorisations SITADEL rapprochées des parcelles historiques. "
                    "Emprise partielle si certaines références restent inconnues ; "
                    "plus_proche désigne une correspondance hors période observée.'"
                )
            )
            statuses = dict(
                connection.execute(
                    text(
                        f"SELECT geolocation_status, count(*) FROM {target_table} "
                        "WHERE source_file IN "
                        "(SELECT DISTINCT source_file FROM pg_temp.sitadel_source) "
                        "GROUP BY geolocation_status"
                    )
                ).all()
            )
            methods = dict(
                connection.execute(
                    text(
                        "SELECT matched.value ->> 'method', count(*) "
                        f"FROM {target_table} "
                        "CROSS JOIN LATERAL jsonb_array_elements(parcel_matches) "
                        "AS matched(value) WHERE source_file IN "
                        "(SELECT DISTINCT source_file FROM pg_temp.sitadel_source) "
                        "GROUP BY matched.value ->> 'method'"
                    )
                ).all()
            )
        logger.info("Géolocalisation SITADEL dans %s : %s.", target_table, statuses)
        uncertain_methods = {
            method: count for method, count in methods.items() if method != "periode"
        }
        if uncertain_methods or set(statuses) - {"complet"}:
            logger.warning(
                "Rapprochements SITADEL incomplets ou hors période observée : "
                "statuts=%s ; méthodes=%s.",
                statuses,
                uncertain_methods,
            )
        return statuses
    finally:
        engine.dispose()
