from pathlib import Path

import typer
from cli.options import (
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.cartofriches.import_cartofriches import import_cartofriches_flow

app = typer.Typer()

OPTIONAL_DIRNAME_CARTOFRICHES_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing Cartofriches GeoPackage file. "
        "Optional (downloads national GeoPackage if omitted)."
    ),
)

FRICHES_CARTOFRICHES_TABLE_OPTION = typer.Option(
    "friches_cartofriches", help="Database table name"
)


@app.command()
def cartofriches(
    dirname: Path = OPTIONAL_DIRNAME_CARTOFRICHES_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = FRICHES_CARTOFRICHES_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    Import des sites référencés dans Cartofriches (friches industrielles,
    commerciales, etc.).

    Base nationale GeoPackage. Si le répertoire n'est pas fourni, le fichier
    GeoPackage est téléchargé automatiquement depuis data.gouv.fr.
    """
    import_cartofriches_flow(
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )
