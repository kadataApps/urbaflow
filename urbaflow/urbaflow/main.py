from typing import List
import typer
from pathlib import Path

from flows.dvf.dvf import dvf_flow
from flows.cadastre.flow_cadastre import (
    STEPS_FLOW_CADASTRE,
    import_cadastre_majic_flow,
)

from flows.locomvac import import_locomvac


app = typer.Typer()


@app.command()
def majic(
    dirname: Path = typer.Argument(
        Path("/data/"),
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


@app.command()
def dvf(
    departement: str,
    dirname: Path = typer.Argument(
        Path("/data/"),
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
):
    dvf_flow._run(departement, dirname)


@app.command()
def locomvac(
    dirname: Path = typer.Argument(
        Path("/data/"),
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


if __name__ == "__main__":
    app()
