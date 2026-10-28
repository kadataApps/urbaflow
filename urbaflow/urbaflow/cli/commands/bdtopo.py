import typer
from cli.options import (
    COMMUNES_OPTION,
    DEPARTMENTS_OPTION,
    EPCI_OPTION,
    KEEP_FILES_OPTION,
    RECREATE_FALSE_OPTION,
    SCHEMA_OPTION,
)
from flows.bdtopo.import_bdtopo_batiment import import_bdtopo_batiment_flow
from flows.bdtopo.import_bdtopo_troncon_route import (
    import_bdtopo_troncon_route_flow,
)
from shared_tasks.config import db_schema as get_import_schema

app = typer.Typer()

BDTOPO_MILLESIME_OPTION = typer.Option(
    None,
    "--millesime",
    help=(
        "Millésime BD TOPO souhaité (ex: '2026-06-15'). "
        "Par défaut, la dernière édition disponible."
    ),
)

BDTOPO_BATIMENT_TABLE_OPTION = typer.Option(
    "bdtopo_batiment", help="Nom de la table cible"
)


@app.command(name="bdtopo-batiment")
def bdtopo_batiment(
    departments: str | None = DEPARTMENTS_OPTION,
    epci: str | None = EPCI_OPTION,
    communes: str | None = COMMUNES_OPTION,
    millesime: str | None = BDTOPO_MILLESIME_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = BDTOPO_BATIMENT_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
    keep_files: bool = KEEP_FILES_OPTION,
) -> None:
    """
    Import des bâtiments de la BD TOPO® IGN depuis la Géoplateforme.

    Le périmètre est défini par un ou plusieurs départements (--departement),
    un EPCI (--epci) ou une liste de codes INSEE de communes (--communes).
    Les bâtiments déjà présents sur le périmètre sont supprimés avant l'import.
    """
    import_bdtopo_batiment_flow(
        departements=departments,
        epci=epci,
        communes=communes,
        edition_date=millesime,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
        keep_files=keep_files,
    )


@app.command(name="bdtopo-troncon-route")
def bdtopo_troncon_route(
    department: str = typer.Option(
        ...,
        "-d",
        "--departement",
        help="Code du département (ex. : 35, 2A, 974).",
    ),
    millesime: str | None = BDTOPO_MILLESIME_OPTION,
    schema: str = typer.Option(
        get_import_schema(),
        "--schema",
        envvar="IMPORT_SCHEMA",
        help="Nom du schéma cible existant.",
    ),
    table_name: str = typer.Option(
        "bdtopo_troncon_de_route", help="Nom de la table cible."
    ),
    keep_files: bool = KEEP_FILES_OPTION,
) -> None:
    """Importe les tronçons de route BD TOPO IGN d'un département."""
    import_bdtopo_troncon_route_flow(
        department=department,
        edition_date=millesime,
        db_schema=schema,
        table_name=table_name,
        keep_files=keep_files,
    )
