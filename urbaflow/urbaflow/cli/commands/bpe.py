from pathlib import Path

import typer
from cli.options import (
    DEPARTMENT_OPTION,
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.bpe.import_bpe import import_bpe_flow

app = typer.Typer()

OPTIONAL_DIRNAME_BPE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire des fichiers CSV BPE. "
        "Par défaut, l'archive nationale BPE est téléchargée."
    ),
)

INSEE_BPE_TABLE_OPTION = typer.Option("insee_bpe", help="Nom de la table cible")


@app.command()
def bpe(
    dirname: Path | None = OPTIONAL_DIRNAME_BPE_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = INSEE_BPE_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Import de la Base Permanente des Équipements (BPE / INSEE).

    Base nationale géolocalisée (équipements, commerces, santé, sports, etc.).
    Filtrable par département (-d/--departement). Si le répertoire n'est pas fourni,
    le fichier ZIP BPE est téléchargé.
    """
    import_bpe_flow(
        department=department,
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )
