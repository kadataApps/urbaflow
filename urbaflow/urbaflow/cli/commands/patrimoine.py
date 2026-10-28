from pathlib import Path

import typer
from cli.options import (
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.acr.import_acr import import_acr_flow
from flows.mh.import_mh import import_mh_flow

app = typer.Typer()

OPTIONAL_DIRNAME_MH_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing MH GeoJSON file. "
        "Optional (downloads national GeoJSON if omitted)."
    ),
)

OPTIONAL_DIRNAME_ACR_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing ACR CSV file. "
        "Optional (downloads national CSV if omitted)."
    ),
)

PATRIMOINE_MH_TABLE_OPTION = typer.Option(
    "patrimoine_immeubles_proteges_mh", help="Database table name"
)

PATRIMOINE_ACR_TABLE_OPTION = typer.Option(
    "patrimoine_architecture_contemporaine_remarquable", help="Database table name"
)


@app.command()
def mh(
    dirname: Path = OPTIONAL_DIRNAME_MH_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = PATRIMOINE_MH_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    Import des immeubles protégés au titre des Monuments Historiques (MH).

    Base nationale GeoJSON. Si le répertoire n'est pas fourni, le fichier GeoJSON
    est téléchargé automatiquement depuis data.gouv.fr.
    """
    import_mh_flow(
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def acr(
    dirname: Path = OPTIONAL_DIRNAME_ACR_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = PATRIMOINE_ACR_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    Import des édifices labellisés Architecture Contemporaine Remarquable (ACR).

    Base nationale CSV. Si le répertoire n'est pas fourni, le fichier CSV
    est téléchargé automatiquement depuis data.gouv.fr.
    """
    import_acr_flow(
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )
