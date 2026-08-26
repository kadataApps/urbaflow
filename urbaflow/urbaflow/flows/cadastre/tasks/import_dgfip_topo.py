import csv
from pathlib import Path

from shared_tasks.db_engine import create_engine
from shared_tasks.logging_config import get_logger
from sqlalchemy import text

SOURCE_FILENAME = "topo-fichier-des-entites-topographiques.csv"
EXPECTED_HEADERS = (
    "code pays",
    "code region",
    "code dep",
    "code commune",
    "code voie",
    "code type topo",
    "nature de voie",
    "libelle",
    "type commune actuel (R ou N)",
    "type commune FIP (R ou NFIP)",
    "RUR actuel",
    "RUR FIP",
    "caractere voie",
    "annulation",
    "date annulation",
    "date creation de article",
    "type voie",
    "mot classant",
    "date derniere transition",
)
RAW_TABLE_COLUMNS = (
    "code_pays",
    "code_region",
    "code_dep",
    "code_commune",
    "code_voie",
    "code_type_topo",
    "nature_voie",
    "libelle",
    "type_commune_actuel",
    "type_commune_fip",
    "rur_actuel",
    "rur_fip",
    "caractere_voie",
    "annulation",
    "date_annulation",
    "date_creation_article",
    "type_voie",
    "mot_classant",
    "date_derniere_transition",
)


def find_source_file(source_dir: Path) -> Path:
    """Retourne le fichier DGFiP TOPO unique attendu dans le répertoire source."""
    source_files = list(source_dir.rglob(SOURCE_FILENAME))
    if len(source_files) != 1:
        raise ValueError(
            f"Le répertoire {source_dir} doit contenir "
            f"un unique fichier {SOURCE_FILENAME}."
        )
    return source_files[0]


def validate_headers(source_file: Path) -> None:
    """Vérifie que le CSV DGFiP TOPO possède le schéma attendu."""
    with source_file.open(encoding="utf-8-sig", newline="") as csv_file:
        headers = next(csv.reader(csv_file, delimiter=";"), None)

    if tuple(headers or []) != EXPECTED_HEADERS:
        raise ValueError(
            "Les colonnes du fichier DGFiP TOPO ne correspondent pas au schéma attendu."
        )


def import_dgfip_topo_file(source_dir: Path) -> None:
    """Charge le CSV DGFiP TOPO dans la table source PostgreSQL."""
    logger = get_logger(__name__)
    source_file = find_source_file(source_dir)
    validate_headers(source_file)

    logger.info("Chargement du fichier DGFiP TOPO %s", source_file)
    engine = create_engine()
    columns = ", ".join(RAW_TABLE_COLUMNS)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS dgfip_topo"))
        connection.execute(
            text(
                f"CREATE TABLE dgfip_topo "
                f"({', '.join(f'{column} text' for column in RAW_TABLE_COLUMNS)})"
            )
        )
        with source_file.open(encoding="utf-8-sig", newline="") as csv_file:
            cursor = connection.connection.cursor()
            cursor.copy_expert(
                f"COPY dgfip_topo ({columns}) FROM STDIN WITH CSV HEADER DELIMITER ';'",
                csv_file,
            )
    logger.info("Chargement des entités topographiques DGFiP terminé")
