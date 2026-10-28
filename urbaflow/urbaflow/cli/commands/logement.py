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

LOVAC_FIL_TABLE_OPTION = typer.Option("lovac_fil", help="Nom de la table cible")

RECURSIVE_OPTION = typer.Option(False, help="Rechercher dans les sous-répertoires")


@app.command()
def locomvac(
    dirname: Path = DIRNAME_ARGUMENT,
) -> None:
    """
    DIRNAME : Chemin du répertoire contenant les fichiers LOCOMVAC
    """
    typer.echo(f"Exécution de l'import LOCOMVAC depuis : {dirname}")
    import_locomvac(dirname)


@app.command()
def lovac(
    dirname: Path = DIRNAME_ARGUMENT,
) -> None:
    """
    DIRNAME : Chemin du répertoire contenant les fichiers csv LOVAC
    """
    typer.echo(f"Exécution de l'import LOVAC depuis : {dirname}")
    import_lovac_flow(dirname=dirname)


@app.command()
def lovac_fil(
    dirname: Path = DIRNAME_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = LOVAC_FIL_TABLE_OPTION,
    recursive: bool = RECURSIVE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    DIRNAME : Chemin du répertoire contenant les fichiers lovac_fil.csv

    Import des données LOVAC FIL (Locaux Vacants Commerciaux - données détaillées)
    """
    typer.echo(f"Exécution de l'import LOVAC FIL depuis : {dirname}")
    typer.echo(f"Cible : {schema}.{table_name}")
    typer.echo(f"Recherche récursive : {recursive}")
    typer.echo(f"Recréation de la table : {recreate}")
    result = import_lovac_fil_flow(
        dirname=dirname,
        schema=schema,
        table_name=table_name,
        recursive=recursive,
        recreate=recreate,
    )
    typer.echo(f"Import terminé avec succès : {result}")
