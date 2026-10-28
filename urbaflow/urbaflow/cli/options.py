from pathlib import Path

import typer
from shared_tasks.config import db_schema as get_import_schema

DEFAULT_DIRNAME = Path("/data/")

DIRNAME_ARGUMENT = typer.Argument(
    DEFAULT_DIRNAME,
    exists=True,
    file_okay=False,
    dir_okay=True,
    writable=True,
    readable=True,
    resolve_path=True,
)

SCHEMA_OPTION = typer.Option(
    get_import_schema(), envvar="IMPORT_SCHEMA", help="Nom du schéma de destination"
)

BANATIC_COMMUNES_TABLE_OPTION = typer.Option(
    "banatic_communes", help="Database table name"
)

RECREATE_TRUE_OPTION = typer.Option(True, help="Drop/recreate table if it exists")

RECREATE_FALSE_OPTION = typer.Option(False, help="Drop/recreate table if it exists")

DEPARTMENT_OPTION = typer.Option(
    None,
    "-d",
    "--departement",
    "--department",
    help="Code du département (ex. : '75' pour Paris).",
)

BDTOPO_DEPARTEMENTS_OPTION = typer.Option(
    None,
    "-d",
    "--departement",
    "--department",
    help=(
        "Code(s) de département séparés par des virgules (ex: '35' ou '35,22'). "
        "Exclusif avec --epci et --communes."
    ),
)

BDTOPO_EPCI_OPTION = typer.Option(
    None,
    "-e",
    "--epci",
    help=(
        "Numéro SIREN de l'EPCI dont les communes doivent être importées. "
        "Exclusif avec --departement et --communes."
    ),
)

BDTOPO_COMMUNES_OPTION = typer.Option(
    None,
    "-c",
    "--communes",
    help=(
        "Codes INSEE de communes séparés par des virgules (ex: '35238,35047'). "
        "Exclusif avec --departement et --epci."
    ),
)

BDTOPO_KEEP_FILES_OPTION = typer.Option(
    False,
    "--keep-files/--no-keep-files",
    help="Conserver l'archive téléchargée et le GeoPackage extrait",
)
