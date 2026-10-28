from pathlib import Path

import typer
from cli.options import (
    DEPARTMENT_OPTION,
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.geosirene.import_geosirene_etablissement import import_geosirene_data
from flows.geosirene.import_sirene_etablissement import (
    create_geosirene_etablissement_detail,
    import_sirene_etablissement_data,
)

app = typer.Typer()

OPTIONAL_DIRNAME_GEOSIRENE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire du fichier GeoParquet GeoSirene. "
        "Par défaut, le fichier GeoParquet national est téléchargé."
    ),
)

OPTIONAL_DIRNAME_SIRENE_ETABLISSEMENT_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire du fichier GeoParquet Sirene Etablissement. "
        "Par défaut, le fichier GeoParquet national est téléchargé."
    ),
)

GEOSIRENE_TABLE_OPTION = typer.Option(
    "geosirene_etablissement", help="Nom de la table cible"
)

SIRENE_ETABLISSEMENT_TABLE_OPTION = typer.Option(
    "sirene_etablissement", help="Nom de la table cible"
)

GEOSIRENE_DETAIL_TABLE_OPTION = typer.Option(
    "geosirene_etablissement_detail", help="Nom de la table cible"
)

FILTER_BY_GEOSIRENE_COMMUNES_OPTION = typer.Option(
    True,
    help=(
        "Limiter l'import Sirene Etablissement aux communes déjà présentes dans "
        "la table geosirene_etablissement (ignoré si --departement est fourni)."
    ),
)


@app.command()
def geosirene(
    dirname: Path | None = OPTIONAL_DIRNAME_GEOSIRENE_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = GEOSIRENE_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Import de la base Sirene des établissements géolocalisés (GeoSirene - GeoParquet).

    Base nationale au format GeoParquet. Filtrable par département (-d/--departement).
    Si le répertoire n'est pas fourni, le fichier GeoParquet est téléchargé.
    """
    import_geosirene_data(
        department=department,
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command(name="sirene-etablissement")
def sirene_etablissement(
    dirname: Path | None = OPTIONAL_DIRNAME_SIRENE_ETABLISSEMENT_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = SIRENE_ETABLISSEMENT_TABLE_OPTION,
    geosirene_table_name: str = GEOSIRENE_TABLE_OPTION,
    filter_by_geosirene_communes: bool = FILTER_BY_GEOSIRENE_COMMUNES_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Import des données descriptives des établissements Sirene (INSEE - GeoParquet).

    Base nationale volumineuse. Filtrable par département (-d/--departement) ou,
    par défaut, sur les communes déjà présentes dans la table
    geosirene_etablissement. Si le répertoire n'est pas fourni, le fichier
    GeoParquet est téléchargé.
    """
    import_sirene_etablissement_data(
        department=department,
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        geosirene_table_name=geosirene_table_name,
        filter_by_geosirene_communes=filter_by_geosirene_communes,
        recreate=recreate,
    )


@app.command(name="geosirene-detail")
def geosirene_detail(
    schema: str = SCHEMA_OPTION,
    detail_table_name: str = GEOSIRENE_DETAIL_TABLE_OPTION,
    geosirene_table_name: str = GEOSIRENE_TABLE_OPTION,
    sirene_table_name: str = SIRENE_ETABLISSEMENT_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Création de la table geosirene_etablissement_detail (jointure entre
    geosirene_etablissement et sirene_etablissement).

    Seuls les établissements présents dans les deux tables sont conservés.
    Nécessite que les tables geosirene_etablissement et sirene_etablissement
    aient été importées au préalable.
    """
    create_geosirene_etablissement_detail(
        db_schema=schema,
        detail_table_name=detail_table_name,
        geosirene_table_name=geosirene_table_name,
        sirene_table_name=sirene_table_name,
        recreate=recreate,
    )
