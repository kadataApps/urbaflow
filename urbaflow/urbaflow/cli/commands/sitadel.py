from pathlib import Path

import typer
from cli.options import SCHEMA_OPTION
from flows.sitadel.download_sitadel import download_sitadel_flow
from flows.sitadel.enrich_commune import enrich_commune_sitadel_flow

app = typer.Typer()

SITADEL_DIRECTORY_ARGUMENT = typer.Argument(
    None,
    file_okay=False,
    dir_okay=True,
    help=(
        "Répertoire de destination, créé si nécessaire. "
        "Par défaut : urbaflow/temp/sitadel."
    ),
)
SITADEL_SOURCE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=True,
    dir_okay=False,
    readable=True,
    help="CSV annuel communal des logements ; téléchargé si absent.",
)


@app.command()
def sitadel(dirname: Path | None = SITADEL_DIRECTORY_ARGUMENT) -> None:
    """Télécharge les CSV SITADEL communaux et détaillés, sans import en base."""
    download_sitadel_flow(dirname=dirname)


@app.command()
def sitadel_indicators(
    source_file: Path | None = SITADEL_SOURCE_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = typer.Option("commune", help="Table des communes à enrichir."),
    code_column: str = typer.Option("code_insee", help="Colonne du code INSEE."),
    population_column: str = typer.Option(
        "population", help="Colonne de la population de référence."
    ),
    end_year: int | None = typer.Option(
        None,
        min=2011,
        help="Dernière année incluse ; par défaut, dernière année civile révolue.",
    ),
) -> None:
    """Ajoute les indicateurs de logements commencés sur dix ans à la table commune."""
    enrich_commune_sitadel_flow(
        source_file=source_file,
        db_schema=schema,
        table_name=table_name,
        code_column=code_column,
        population_column=population_column,
        end_year=end_year,
    )
