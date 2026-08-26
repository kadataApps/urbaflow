from pathlib import Path

import typer
from dotenv import load_dotenv
from flows.cadastre.flow_cadastre import (
    STEPS_FLOW_CADASTRE,
    import_cadastre_majic_flow,
)
from flows.cadastre.flow_dgfip_topo import import_dgfip_topo_flow
from flows.dvf.dvf import dvf_flow
from flows.georisques.import_cavite import import_risques_cavite_flow
from flows.georisques.import_rga import import_rga_flow
from flows.locomvac import import_locomvac
from flows.lovac.import_lovac import import_lovac_flow
from flows.lovac.import_lovac_fil import import_lovac_fil_flow
from shared_tasks.logging_config import setup_logging

# Load environment variables from .env file in the root directory
load_dotenv(Path(__file__).parent.parent.parent / ".env")

setup_logging()

app = typer.Typer()

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

STEPS_ARGUMENT = typer.Argument(
    None,
    help=(
        "List of steps to run (e.g., 'step1', 'step2'). "
        "If not provided, all steps are run."
    ),
)

OPTIONAL_DIRNAME_CAVITE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help="Directory path containing CSV files. Optional if --department is provided.",
)

OPTIONAL_DIRNAME_RGA_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing RGA shapefiles. "
        "Optional if --departement is provided."
    ),
)

SCHEMA_OPTION = typer.Option("public", help="Database schema name")
LOVAC_FIL_TABLE_OPTION = typer.Option("lovac_fil", help="Database table name")
RISQUES_CAVITE_TABLE_OPTION = typer.Option("risques_cavite", help="Database table name")
RECURSIVE_OPTION = typer.Option(False, help="Search recursively in subdirectories")
RECREATE_TRUE_OPTION = typer.Option(True, help="Drop/recreate table if it exists")
RECREATE_FALSE_OPTION = typer.Option(False, help="Drop/recreate table if it exists")
DEPARTMENT_OPTION = typer.Option(
    None,
    "-d",
    "--department",
    help="Department code (e.g., '75' for Paris). Required if dirname is not provided.",
)
DEPARTEMENT_OPTION = typer.Option(
    None,
    "-d",
    "--departement",
    help="Department code (e.g., '75' for Paris). Required if dirname is not provided.",
)


@app.command()
def dvf(
    departements: str,
    dirname: Path = DIRNAME_ARGUMENT,
):
    dvf_flow._run(departements, dirname)


@app.command(name="dgfip-topo")
def dgfip_topo(
    dirname: Path = DIRNAME_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant le fichier des entités topographiques DGFiP
    """
    import_dgfip_topo_flow(path=dirname)


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


@app.command()
def majic(
    dirname: Path = DIRNAME_ARGUMENT,
    steps: list[str] = STEPS_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers MAJIC
    """
    if steps:
        # ensure step names are valid
        for step in steps:
            if step not in STEPS_FLOW_CADASTRE.keys():
                raise typer.BadParameter(
                    f"Invalid step name '{step}'. "
                    f"Valid step names are: {STEPS_FLOW_CADASTRE.keys()}"
                )

    steps_to_process = steps if steps else STEPS_FLOW_CADASTRE.keys()

    import_cadastre_majic_flow(path=dirname, enabled_steps=steps_to_process)


@app.command()
def risques_cavite(
    dirname: Path = OPTIONAL_DIRNAME_CAVITE_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_CAVITE_TABLE_OPTION,
):
    """
    Import des données de risques de cavités.

    DIRNAME : Chemin optionnel du répertoire contenant les fichiers CSV de cavités.
    Si non fourni, l'option --department (-d) doit être spécifiée.
    """
    # Validate that at least one of dirname or department is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --department (-d) option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_cavite_flow(
        path=dirname,
        department=department,
        recreate=recreate,
        schema=schema,
        table_name=table_name,
    )


@app.command()
def risques_rga(
    dirname: Path = OPTIONAL_DIRNAME_RGA_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données de risques de retrait-gonflement des argiles (RGA).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_rga_flow(
        dirname=dirname,
        department=departement,
        schema=schema,
        replace=recreate,
    )


if __name__ == "__main__":
    app()
