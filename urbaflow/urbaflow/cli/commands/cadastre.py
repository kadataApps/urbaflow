from pathlib import Path

import typer
from cli.options import (
    BDTOPO_COMMUNES_OPTION,
    BDTOPO_DEPARTEMENTS_OPTION,
    BDTOPO_EPCI_OPTION,
    DIRNAME_ARGUMENT,
)
from flows.cadastre.flow_cadastre import (
    STEPS_FLOW_CADASTRE,
    import_cadastre_majic_flow,
)
from flows.cadastre.flow_dgfip_topo import import_dgfip_topo_flow
from flows.cadastre.import_dgfip_geoparquet import (
    DEFAULT_PARQUET_URL,
    import_dgfip_geoparquet_flow,
)

app = typer.Typer()

OPTIONAL_DIRNAME_DGFIP_TOPO_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help=(
        "Répertoire contenant le CSV DGFiP TOPO. "
        "Si omis, le fichier est téléchargé depuis data.gouv.fr."
    ),
)

CADASTRE_SOURCE_OPTION = typer.Option(
    DEFAULT_PARQUET_URL,
    "--source",
    help="URL ou chemin local du fichier cadastral GeoParquet.",
)
CADASTRE_SCHEMA_OPTION = typer.Option(
    "public",
    "--schema",
    envvar="IMPORT_SCHEMA",
    help="Schéma de destination PostgreSQL.",
)

STEPS_ARGUMENT = typer.Argument(
    None,
    help=(
        "Liste des étapes à exécuter (ex. : 'step1', 'step2'). "
        "Par défaut, toutes les étapes sont exécutées."
    ),
)


@app.command(name="dgfip-topo")
def dgfip_topo(
    dirname: Path | None = OPTIONAL_DIRNAME_DGFIP_TOPO_ARGUMENT,
) -> None:
    """Importe les entités topographiques DGFiP depuis un répertoire ou data.gouv.fr."""
    import_dgfip_topo_flow(path=dirname)


@app.command(name="dgfip-geoparquet")
def dgfip_geoparquet(
    departments: str | None = BDTOPO_DEPARTEMENTS_OPTION,
    epci: str | None = BDTOPO_EPCI_OPTION,
    communes: str | None = BDTOPO_COMMUNES_OPTION,
    schema: str = CADASTRE_SCHEMA_OPTION,
    source: str = CADASTRE_SOURCE_OPTION,
) -> None:
    """Importe les contours DGFiP : communes, sections et bâtiments."""
    import_dgfip_geoparquet_flow(
        departements=departments,
        epci=epci,
        communes=communes,
        db_schema=schema,
        source=source,
    )


@app.command()
def majic(
    dirname: Path = DIRNAME_ARGUMENT,
    steps: list[str] | None = STEPS_ARGUMENT,
) -> None:
    """
    DIRNAME : Chemin du répertoire contenant les fichiers MAJIC
    """
    if steps:
        for step in steps:
            if step not in STEPS_FLOW_CADASTRE.keys():
                raise typer.BadParameter(
                    f"Étape inconnue '{step}'. "
                    f"Étapes disponibles : {STEPS_FLOW_CADASTRE.keys()}"
                )

    steps_to_process = steps if steps else STEPS_FLOW_CADASTRE.keys()

    import_cadastre_majic_flow(path=dirname, enabled_steps=steps_to_process)
