from typing import List
import typer
from pathlib import Path
from dotenv import load_dotenv

from flows.cadastre.flow_fantoir import import_fantoir_flow
from flows.dvf.dvf import dvf_flow
from flows.cadastre.flow_cadastre import (
    STEPS_FLOW_CADASTRE,
    import_cadastre_majic_flow,
)

from flows.locomvac import import_locomvac
from flows.lovac.import_lovac import import_lovac_flow
from flows.lovac.import_lovac_fil import import_lovac_fil_flow

from shared_tasks.logging_config import setup_logging

# Load environment variables from .env file in the root directory
load_dotenv(Path(__file__).parent.parent.parent / ".env")

setup_logging()

app = typer.Typer()

DEFAULT_DIRNAME = Path("/data/")


@app.command()
def dvf(
    departements: str,
    dirname: Path = typer.Argument(
        DEFAULT_DIRNAME,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
):
    dvf_flow._run(departements, dirname)


@app.command()
def fantoir(
    dirname: Path = typer.Argument(
        DEFAULT_DIRNAME,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers FANTOIR
    """
    import_fantoir_flow._run(path=dirname)


@app.command()
def locomvac(
    dirname: Path = typer.Argument(
        DEFAULT_DIRNAME,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers LOCOMVAC
    """
    typer.echo(f"Running LocomVac flow in directory: {dirname}")
    import_locomvac(dirname)


@app.command()
def lovac(
    dirname: Path = typer.Argument(
        DEFAULT_DIRNAME,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers csv LOVAC
    """
    typer.echo(f"Running Lovac flow in directory: {dirname}")
    import_lovac_flow(dirname=dirname)


@app.command()
def lovac_fil(
    dirname: Path = typer.Argument(
        DEFAULT_DIRNAME,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    schema: str = typer.Option("public", help="Database schema name"),
    table_name: str = typer.Option("lovac_fil", help="Database table name"),
    recursive: bool = typer.Option(False, help="Search recursively in subdirectories"),
    recreate: bool = typer.Option(True, help="Drop/recreate table if it exists"),
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


@app.command()
def majic(
    dirname: Path = typer.Argument(
        DEFAULT_DIRNAME,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    steps: List[str] = typer.Argument(
        None,
        help="List of steps to run (e.g., 'step1', 'step2'). If not provided, all steps are run.",
    ),
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers MAJIC
    """
    if steps:
        # ensure step names are valid
        for step in steps:
            if step not in STEPS_FLOW_CADASTRE.keys():
                raise typer.BadParameter(
                    f"Invalid step name '{step}'. Valid step names are: {STEPS_FLOW_CADASTRE.keys()}"
                )

    steps_to_process = steps if steps else STEPS_FLOW_CADASTRE.keys()

    import_cadastre_majic_flow._run(path=dirname, enabled_steps=steps_to_process)


if __name__ == "__main__":
    app()
