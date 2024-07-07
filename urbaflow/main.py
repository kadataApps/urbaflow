import typer
from pathlib import Path

from urbaflow.flows.dvf.download_dvf_from_imported_data import flow_dvf
from urbaflow.flows.cadastre.flow_cadastre import (
    flow_clean,
    flow_copy_transform_majic_queries,
    flow_cadastre,
    STEPS_FLOW_CADASTRE,
)
from urbaflow.flows.cadastre.tasks.fantoir_import_db import (
    create_fantoir,
    formatage_fantoir,
    truncate_fantoir_tables,
)
from urbaflow.flows.cadastre.tasks.fantoir_import_file import import_fantoir_file
from urbaflow.flows.locomvac import import_locomvac


app = typer.Typer()


@app.command()
def fantoir(
    dirname: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    import_file: bool = typer.Option(
        True, help="Import fantoir raw files to db in specified schema in config.ini"
    ),
    create_tables: bool = typer.Option(True, help="create tables communes, voies"),
    empty_tables: bool = typer.Option(False, help="truncates tables communes, voies"),
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers FANTOIR
    """
    flow_copy_transform_majic_queries()  # copy sql scripts
    if import_file is True:
        import_fantoir_file(path=dirname).start_import()
    if create_tables is True:
        create_fantoir()
    if empty_tables is True:
        truncate_fantoir_tables()
    formatage_fantoir()
    flow_clean()


@app.command()
def majic(
    dirname: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    step1: bool = typer.Option(
        STEPS_FLOW_CADASTRE["1"]["default"],
        help=STEPS_FLOW_CADASTRE["1"]["description"],
    ),
    step2: bool = typer.Option(
        STEPS_FLOW_CADASTRE["2"]["default"],
        help=STEPS_FLOW_CADASTRE["2"]["description"],
    ),
    step3: bool = typer.Option(
        STEPS_FLOW_CADASTRE["3"]["default"],
        help=STEPS_FLOW_CADASTRE["3"]["description"],
    ),
    step4: bool = typer.Option(
        STEPS_FLOW_CADASTRE["4"]["default"],
        help=STEPS_FLOW_CADASTRE["4"]["description"],
    ),
    step5: bool = typer.Option(
        STEPS_FLOW_CADASTRE["5"]["default"],
        help=STEPS_FLOW_CADASTRE["5"]["description"],
    ),
    step6: bool = typer.Option(
        STEPS_FLOW_CADASTRE["6"]["default"],
        help=STEPS_FLOW_CADASTRE["6"]["description"],
    ),
    step7: bool = typer.Option(
        STEPS_FLOW_CADASTRE["7"]["default"],
        help=STEPS_FLOW_CADASTRE["7"]["description"],
    ),
    step8: bool = typer.Option(
        STEPS_FLOW_CADASTRE["8"]["default"],
        help=STEPS_FLOW_CADASTRE["8"]["description"],
    ),
    step9: bool = typer.Option(
        STEPS_FLOW_CADASTRE["9"]["default"],
        help=STEPS_FLOW_CADASTRE["9"]["description"],
    ),
    step10: bool = typer.Option(
        STEPS_FLOW_CADASTRE["10"]["default"],
        help=STEPS_FLOW_CADASTRE["10"]["description"],
    ),
    step11: bool = typer.Option(
        STEPS_FLOW_CADASTRE["11"]["default"],
        help=STEPS_FLOW_CADASTRE["11"]["description"],
    ),
    step12: bool = typer.Option(
        STEPS_FLOW_CADASTRE["12"]["default"],
        help=STEPS_FLOW_CADASTRE["12"]["description"],
    ),
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers MAJIC
    """

    if dirname.is_dir():
        typer.echo(f"Using {dirname}")
        steps_to_process = {
            "1": {"default": step1},
            "2": {"default": step2},
            "3": {"default": step3},
            "4": {"default": step4},
            "5": {"default": step5},
            "6": {"default": step6},
            "7": {"default": step7},
            "8": {"default": step8},
            "9": {"default": step9},
            "10": {"default": step10},
            "11": {"default": step11},
            "12": {"default": step12},
        }
        flow_cadastre(path=dirname, steps=steps_to_process)


@app.command()
def dvf(
    departement: str,
    dirname: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
):
    flow_dvf(departement, dirname)


if __name__ == "__main__":
    app()

@app.command()
def locomvac(dirname: Path = typer.Argument(
        "/data/",
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    )):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers LOCOMVAC
    """
    typer.echo(f"Running LocomVac flow in directory: {dirname}")
    import_locomvac(dirname)