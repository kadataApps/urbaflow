from pathlib import Path

import typer
from cli.options import (
    COMMUNES_OPTION,
    DEPARTMENTS_OPTION,
    DIRNAME_ARGUMENT,
    EPCI_OPTION,
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
from flows.cadastre.import_parcelles_historique import (
    ETALAB_CADASTRE_URL,
    import_parcelles_historique_flow,
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

HISTORY_DEPARTMENTS_OPTION = typer.Option(
    None,
    "-d",
    "--departement",
    help=(
        "Code(s) de département séparés par des virgules (ex: '35' ou '35,22'). "
        "Par défaut, tous les départements publiés."
    ),
)
HISTORY_MILLESIMES_OPTION = typer.Option(
    None,
    "-m",
    "--millesimes",
    help=(
        "Millésime(s) AAAA-MM-JJ séparés par des virgules. Par défaut, tous les "
        "millésimes publiés depuis le 2018-04-03 et non encore importés."
    ),
)
HISTORY_SOURCE_OPTION = typer.Option(
    ETALAB_CADASTRE_URL,
    "--source",
    help="URL ou répertoire local reproduisant l'arborescence etalab-cadastre.",
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
    departments: str | None = DEPARTMENTS_OPTION,
    epci: str | None = EPCI_OPTION,
    communes: str | None = COMMUNES_OPTION,
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


@app.command(name="parcelles-historique")
def parcelles_historique(
    departments: str | None = HISTORY_DEPARTMENTS_OPTION,
    millesimes: str | None = HISTORY_MILLESIMES_OPTION,
    schema: str = CADASTRE_SCHEMA_OPTION,
    source: str = HISTORY_SOURCE_OPTION,
) -> None:
    """Construit ou complète de manière incrémentale l'historique des parcelles."""
    import_parcelles_historique_flow(
        departements=departments,
        millesimes=millesimes,
        db_schema=schema,
        base_location=source,
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
