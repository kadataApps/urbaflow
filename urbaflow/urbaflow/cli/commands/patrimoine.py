from pathlib import Path

import typer
from cli.options import (
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.acr.import_acr import import_acr_flow
from flows.mh.import_mh import import_mh_flow

app = typer.Typer()

OPTIONAL_DIRNAME_MH_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire du fichier GeoJSON MH. "
        "Par défaut, le fichier GeoJSON national est téléchargé."
    ),
)

OPTIONAL_DIRNAME_ACR_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire du fichier CSV ACR. "
        "Par défaut, le fichier CSV national est téléchargé."
    ),
)

PATRIMOINE_MH_TABLE_OPTION = typer.Option(
    "patrimoine_immeubles_proteges_mh", help="Nom de la table cible"
)

PATRIMOINE_ACR_TABLE_OPTION = typer.Option(
    "patrimoine_architecture_contemporaine_remarquable", help="Nom de la table cible"
)


@app.command()
def mh(
    dirname: Path | None = OPTIONAL_DIRNAME_MH_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = PATRIMOINE_MH_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Import des immeubles protégés au titre des Monuments Historiques (MH).

    Base nationale GeoJSON. Si le répertoire n'est pas fourni, le fichier GeoJSON
    est téléchargé automatiquement depuis data.gouv.fr.
    """
    import_mh_flow(
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def acr(
    dirname: Path | None = OPTIONAL_DIRNAME_ACR_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = PATRIMOINE_ACR_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Import des édifices labellisés Architecture Contemporaine Remarquable (ACR).

    Base nationale CSV. Si le répertoire n'est pas fourni, le fichier CSV
    est téléchargé automatiquement depuis data.gouv.fr.
    """
    import_acr_flow(
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )
