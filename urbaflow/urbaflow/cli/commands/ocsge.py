import typer
from cli.options import (
    BDTOPO_COMMUNES_OPTION,
    BDTOPO_DEPARTEMENTS_OPTION,
    BDTOPO_EPCI_OPTION,
    BDTOPO_KEEP_FILES_OPTION,
    RECREATE_FALSE_OPTION,
    SCHEMA_OPTION,
)
from flows.ocsge.import_ocsge import import_ocsge_flow

app = typer.Typer()

OCSGE_MILLESIME_OPTION = typer.Option(
    None,
    "--millesime",
    help=(
        "Millésime OCS GE souhaité (ex: '2023-01-01'). Par défaut, la dernière "
        "édition complète disponible (les livraisons différentielles sont ignorées)."
    ),
)

OCSGE_OCCUPATION_SOL_TABLE_OPTION = typer.Option(
    "ocsge_occupation_sol", help="Database table name"
)

OCSGE_ZONE_CONSTRUITE_TABLE_OPTION = typer.Option(
    "ocsge_zone_construite", help="Database table name"
)


@app.command(name="ocsge")
def ocsge(
    departments: str = BDTOPO_DEPARTEMENTS_OPTION,
    epci: str = BDTOPO_EPCI_OPTION,
    communes: str = BDTOPO_COMMUNES_OPTION,
    millesime: str = OCSGE_MILLESIME_OPTION,
    db_schema: str = SCHEMA_OPTION,
    occupation_sol_table: str = OCSGE_OCCUPATION_SOL_TABLE_OPTION,
    zone_construite_table: str = OCSGE_ZONE_CONSTRUITE_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
    keep_files: bool = BDTOPO_KEEP_FILES_OPTION,
):
    """
    Import des données OCS GE (Occupation du Sol à Grande Échelle) de l'IGN
    depuis la Géoplateforme.

    Le périmètre est défini par un ou plusieurs départements (--departement),
    un EPCI (--epci) ou une liste de codes INSEE de communes (--communes). Pour
    un périmètre EPCI ou communes, seuls les polygones intersectant les contours
    communaux (récupérés depuis l'API Découpage administratif) sont conservés.
    Les données déjà présentes sur le périmètre sont supprimées avant l'import.
    """
    import_ocsge_flow(
        departements=departments,
        epci=epci,
        communes=communes,
        edition_date=millesime,
        db_schema=db_schema,
        occupation_sol_table=occupation_sol_table,
        zone_construite_table=zone_construite_table,
        recreate=recreate,
        keep_files=keep_files,
    )
