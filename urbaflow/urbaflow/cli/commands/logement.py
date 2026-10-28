from pathlib import Path

import typer
from cli.options import (
    DIRNAME_ARGUMENT,
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.locomvac import import_locomvac
from flows.lovac.import_lovac import import_lovac_flow
from flows.lovac.import_lovac_fil import import_lovac_fil_flow

app = typer.Typer()

LOVAC_FIL_TABLE_OPTION = typer.Option("lovac_fil", help="Database table name")

RECURSIVE_OPTION = typer.Option(False, help="Search recursively in subdirectories")


@app.command()
def locomvac(
    dirname: Path = DIRNAME_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers LOCOMVAC
    """
    typer.echo(f"Running LocomVac flow in directory: {dirname}")
    import_locomvac(dirname)


@app.command()
def lovac(
    dirname: Path = DIRNAME_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers csv LOVAC
    """
    typer.echo(f"Running Lovac flow in directory: {dirname}")
    import_lovac_flow(dirname=dirname)


@app.command()
def lovac_fil(
    dirname: Path = DIRNAME_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = LOVAC_FIL_TABLE_OPTION,
    recursive: bool = RECURSIVE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers lovac_fil.csv

    Import des données LOVAC FIL (Locaux Vacants Commerciaux - données détaillées)
    """
    typer.echo(f"Running Lovac FIL flow in directory: {dirname}")
    typer.echo(f"Target: {schema}.{table_name}")
    typer.echo(f"Recursive search: {recursive}")
    typer.echo(f"Recreate table: {recreate}")
    result = import_lovac_fil_flow(
        dirname=dirname,
        schema=schema,
        table_name=table_name,
        recursive=recursive,
        recreate=recreate,
    )
    typer.echo(f"Import completed successfully: {result}")
