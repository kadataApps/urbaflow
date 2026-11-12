import csv
import re
from datetime import date
from pathlib import Path

from prefect import flow
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine, quote_identifier
from shared_tasks.logging_config import get_logger
from sqlalchemy import inspect, text

from .download_sitadel import download_sitadel_file

logger = get_logger(__name__)

ANNUAL_HOUSING_FILENAME = "sitadel_communes_logements_annuels.csv"
HOUSING_TYPES = {
    "Tous Logements",
    "Collectif",
    "Individuel pur",
    "Individuel groupe",
    "Residence",
}
COUNT_COLUMNS = (
    "housing_created_10y",
    "collective_housing_created_10y",
    "individual_housing_created_10y",
)
RATE_COLUMN = "housing_created_10y_per_1000_inhabitants"


def read_housing_indicators(
    source_file: Path, end_year: int
) -> list[dict[str, str | int | None]]:
    """Cumule LOG_COM par commune sur dix années, sans sommer les sous-totaux.

    Une valeur vide ou une année/type absent rend l'indicateur concerné inconnu.
    Les individuels incluent les types pur et groupé ; le total inclut aussi
    les résidences, déjà comptées dans la ligne « Tous Logements ».
    """
    expected_years = set(range(end_year - 9, end_year + 1))
    available_years: set[int] = set()
    observations: dict[str, dict[str, dict[int, int | None]]] = {}
    with source_file.open(encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file, delimiter=";")
        required_columns = {"ANNEE", "COMM", "TYPE_LGT", "LOG_COM"}
        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError(
                "Le CSV SITADEL doit contenir ANNEE, COMM, TYPE_LGT et LOG_COM."
            )
        for row in reader:
            year_text = (row["ANNEE"] or "").strip()
            if not re.fullmatch(r"[0-9]{4}", year_text):
                raise ValueError(
                    f"Année SITADEL invalide à la ligne {reader.line_num}."
                )
            year = int(year_text)
            if year not in expected_years:
                continue
            code = (row["COMM"] or "").strip().upper()
            housing_type = (row["TYPE_LGT"] or "").strip()
            count_text = row["LOG_COM"]
            if (
                not re.fullmatch(r"(?:[0-9]{5}|2[AB][0-9]{3})", code)
                or housing_type not in HOUSING_TYPES
                or count_text is None
            ):
                raise ValueError(
                    f"Ligne SITADEL invalide à la ligne {reader.line_num}."
                )
            count_text = count_text.strip()
            if count_text and not re.fullmatch(r"[0-9]+", count_text):
                raise ValueError(
                    f"LOG_COM invalide à la ligne {reader.line_num} : {count_text!r}."
                )
            annual_counts = observations.setdefault(code, {}).setdefault(
                housing_type, {}
            )
            if year in annual_counts:
                raise ValueError(
                    f"Doublon SITADEL : commune {code}, année {year}, "
                    f"type {housing_type}."
                )
            annual_counts[year] = int(count_text) if count_text else None
            available_years.add(year)

    missing_years = sorted(expected_years - available_years)
    if missing_years:
        raise ValueError(
            f"Années absentes du fichier SITADEL : {missing_years}. "
            "Fournir un fichier à jour ou ajuster --end-year."
        )

    def sum_complete_counts(
        by_type: dict[str, dict[int, int | None]], types: tuple[str, ...]
    ) -> int | None:
        """Additionne uniquement des séries couvrant toutes les années demandées."""
        total = 0
        for housing_type in types:
            annual_counts = by_type.get(housing_type, {})
            if annual_counts.keys() != expected_years:
                return None
            for count in annual_counts.values():
                if count is None:
                    return None
                total += count
        return total

    indicators = [
        {
            "code_insee": code,
            COUNT_COLUMNS[0]: sum_complete_counts(by_type, ("Tous Logements",)),
            COUNT_COLUMNS[1]: sum_complete_counts(by_type, ("Collectif",)),
            COUNT_COLUMNS[2]: sum_complete_counts(
                by_type, ("Individuel pur", "Individuel groupe")
            ),
        }
        for code, by_type in observations.items()
    ]
    incomplete_count = sum(
        any(row[column] is None for column in COUNT_COLUMNS) for row in indicators
    )
    if incomplete_count:
        logger.warning(
            "%d commune(s) ont des séries SITADEL incomplètes sur %d–%d : "
            "les indicateurs concernés restent NULL.",
            incomplete_count,
            end_year - 9,
            end_year,
        )
    return indicators


@flow
def enrich_commune_sitadel_flow(
    source_file: Path | None = None,
    db_schema: str = "public",
    table_name: str = "commune",
    code_column: str = "code_insee",
    population_column: str = "population",
    end_year: int | None = None,
) -> None:
    """Ajoute et actualise les quatre indicateurs SITADEL dans une transaction.

    Par défaut, la période couvre les dix dernières années civiles révolues.
    Les logements créés sont approchés par les logements commencés (LOG_COM),
    non par les autorisations ni les achèvements. La population est celle de
    la table cible, sans extrapolation ni somme de populations annuelles.
    """
    end_year = date.today().year - 1 if end_year is None else end_year
    if not 2011 <= end_year < date.today().year:
        raise ValueError(
            "L'année de fin doit être au moins 2011 et antérieure à l'année courante."
        )
    if code_column == population_column or {code_column, population_column} & {
        *COUNT_COLUMNS,
        RATE_COLUMN,
    }:
        raise ValueError(
            "Les colonnes source et les indicateurs doivent être distincts."
        )

    if source_file is None:
        source_file = download_sitadel_file(
            ANNUAL_HOUSING_FILENAME, TEMP_DIR / "sitadel"
        )
    indicators = read_housing_indicators(Path(source_file), end_year)
    target_table = f"{quote_identifier(db_schema)}.{quote_identifier(table_name)}"
    code = quote_identifier(code_column)
    population = quote_identifier(population_column)
    engine = create_engine(schema=db_schema)
    try:
        with engine.begin() as connection:
            target_columns = {
                column["name"]
                for column in inspect(connection).get_columns(
                    table_name, schema=db_schema
                )
            }
            missing_columns = {code_column, population_column} - target_columns
            if missing_columns:
                raise ValueError(
                    f"Colonnes absentes de {db_schema}.{table_name} : "
                    f"{', '.join(sorted(missing_columns))}."
                )
            connection.execute(
                text(
                    "CREATE TEMPORARY TABLE sitadel_housing_indicators ("
                    "code_insee text PRIMARY KEY, "
                    + ", ".join(f"{column} bigint" for column in COUNT_COLUMNS)
                    + ") ON COMMIT DROP"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO pg_temp.sitadel_housing_indicators VALUES "
                    "(:code_insee, :housing_created_10y, "
                    ":collective_housing_created_10y, :individual_housing_created_10y)"
                ),
                indicators,
            )
            matched_count = connection.execute(
                text(
                    f"SELECT count(*) FROM {target_table} AS commune "
                    "JOIN pg_temp.sitadel_housing_indicators AS indicators "
                    f"ON commune.{code} = indicators.code_insee"
                )
            ).scalar_one()
            if not matched_count:
                raise ValueError(
                    "Aucune commune cible ne correspond aux codes INSEE SITADEL."
                )
            connection.execute(
                text(
                    f"ALTER TABLE {target_table} "
                    + ", ".join(
                        f"ADD COLUMN IF NOT EXISTS {column} bigint"
                        for column in COUNT_COLUMNS
                    )
                    + f", ADD COLUMN IF NOT EXISTS {RATE_COLUMN} numeric"
                )
            )
            connection.execute(
                text(
                    f"UPDATE {target_table} AS target SET "
                    + ", ".join(
                        f"{column} = source.{column}" for column in COUNT_COLUMNS
                    )
                    + f", {RATE_COLUMN} = CASE WHEN target.{population} > 0 "
                    f"THEN source.housing_created_10y * 1000.0 / target.{population} "
                    "ELSE NULL END "
                    f"FROM (SELECT commune.{code} AS code_insee, "
                    + ", ".join(f"indicators.{column}" for column in COUNT_COLUMNS)
                    + " "
                    f"FROM {target_table} AS commune "
                    "LEFT JOIN pg_temp.sitadel_housing_indicators AS indicators "
                    f"ON commune.{code} = indicators.code_insee) AS source "
                    f"WHERE target.{code} IS NOT DISTINCT FROM source.code_insee"
                )
            )
            for column in (*COUNT_COLUMNS, RATE_COLUMN):
                description = (
                    f"SITADEL LOG_COM {end_year - 9}-{end_year} : logements commencés. "
                    "NULL si série incomplète ou commune absente."
                )
                if column == COUNT_COLUMNS[0]:
                    description += " Tous logements, résidences comprises."
                elif column == COUNT_COLUMNS[1]:
                    description += " Logements collectifs, hors résidences."
                elif column == COUNT_COLUMNS[2]:
                    description += " Logements individuels purs et groupés."
                if column == RATE_COLUMN:
                    description += (
                        f" Pour 1000 habitants selon {population_column} ; "
                        "NULL si population nulle, inconnue ou négative."
                    )
                connection.execute(
                    text(
                        f"COMMENT ON COLUMN {target_table}.{column} IS "
                        "'" + description.replace("'", "''") + "'"
                    )
                )
            missing_count = connection.execute(
                text(
                    f"SELECT count(*) FROM {target_table} "
                    f"WHERE housing_created_10y IS NULL OR {RATE_COLUMN} IS NULL"
                )
            ).scalar_one()
            if missing_count:
                logger.warning(
                    "%d commune(s) sans total décennal ou taux calculable ; "
                    "les valeurs inconnues restent NULL.",
                    missing_count,
                )
        logger.info(
            "Indicateurs SITADEL %d–%d actualisés dans %s.%s (%d correspondances).",
            end_year - 9,
            end_year,
            db_schema,
            table_name,
            matched_count,
        )
    finally:
        engine.dispose()
