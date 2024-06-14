import typer
from pathlib import Path

from flows.dvf.download_DVF_from_imported_data import flow_dvf
from flows.cadastre.flow_cadastre import (
    flow_clean,
    flow_copy_transform_majic_queries,
    flow_cadastre,
    STEPS_FLOW_CADASTRE,
)
from flows.cadastre.tasks.fantoir_import_db import (
    create_fantoir,
    formatage_fantoir,
    truncate_fantoir_tables,
)
from flows.cadastre.tasks.fantoir_import_file import import_fantoir_file


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
    etape1: bool = typer.Option(
        STEPS_FLOW_CADASTRE["1"]["default"],
        help=STEPS_FLOW_CADASTRE["1"]["description"],
    ),
    etape2: bool = typer.Option(
        STEPS_FLOW_CADASTRE["2"]["default"],
        help=STEPS_FLOW_CADASTRE["2"]["description"],
    ),
    etape3: bool = typer.Option(
        STEPS_FLOW_CADASTRE["3"]["default"],
        help=STEPS_FLOW_CADASTRE["3"]["description"],
    ),
    etape4: bool = typer.Option(
        STEPS_FLOW_CADASTRE["4"]["default"],
        help=STEPS_FLOW_CADASTRE["4"]["description"],
    ),
    etape5: bool = typer.Option(
        STEPS_FLOW_CADASTRE["5"]["default"],
        help=STEPS_FLOW_CADASTRE["5"]["description"],
    ),
    etape6: bool = typer.Option(
        STEPS_FLOW_CADASTRE["6"]["default"],
        help=STEPS_FLOW_CADASTRE["6"]["description"],
    ),
    etape7: bool = typer.Option(
        STEPS_FLOW_CADASTRE["7"]["default"],
        help=STEPS_FLOW_CADASTRE["7"]["description"],
    ),
    etape8: bool = typer.Option(
        STEPS_FLOW_CADASTRE["8"]["default"],
        help=STEPS_FLOW_CADASTRE["8"]["description"],
    ),
    etape9: bool = typer.Option(
        STEPS_FLOW_CADASTRE["9"]["default"],
        help=STEPS_FLOW_CADASTRE["9"]["description"],
    ),
    etape10: bool = typer.Option(
        STEPS_FLOW_CADASTRE["10"]["default"],
        help=STEPS_FLOW_CADASTRE["10"]["description"],
    ),
    etape11: bool = typer.Option(
        STEPS_FLOW_CADASTRE["11"]["default"],
        help=STEPS_FLOW_CADASTRE["11"]["description"],
    ),
    etape12: bool = typer.Option(
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
            "1": {"default": etape1},
            "2": {"default": etape2},
            "3": {"default": etape3},
            "4": {"default": etape4},
            "5": {"default": etape5},
            "6": {"default": etape6},
            "7": {"default": etape7},
            "8": {"default": etape8},
            "9": {"default": etape9},
            "10": {"default": etape10},
            "11": {"default": etape11},
            "12": {"default": etape12},
        }
        flow_cadastre(path=dirname, etapes=steps_to_process)


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
