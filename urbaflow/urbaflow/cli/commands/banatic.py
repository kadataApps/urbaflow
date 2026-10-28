from pathlib import Path

import typer
from cli.options import (
    BANATIC_COMMUNES_TABLE_OPTION,
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.banatic.import_banatic_communes import import_banatic_communes_flow

app = typer.Typer()

OPTIONAL_DIRNAME_BANATIC_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire des fichiers CSV BANATIC. "
        "Par défaut, les derniers fichiers CSV de data.gouv.fr sont téléchargés."
    ),
)


@app.command(name="banatic-communes")
def banatic_communes(
    dirname: Path | None = OPTIONAL_DIRNAME_BANATIC_ARGUMENT,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = BANATIC_COMMUNES_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Import de la table des communes BANATIC avec le raccordement aux EPCI FP.

    Consolide la liste des communes avec les informations de leur EPCI FP.
    Si le répertoire n'est pas fourni, le téléchargement s'effectue depuis data.gouv.fr.
    """
    epci_file = dirname / "epci_fp.csv" if dirname else None
    communes_file = dirname / "communes_siren.csv" if dirname else None

    import_banatic_communes_flow(
        epci_fp_file=epci_file,
        communes_siren_file=communes_file,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )
