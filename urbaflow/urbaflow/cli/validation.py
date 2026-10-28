from pathlib import Path

import typer


def require_directory_or_department(
    directory: Path | None, department: str | None
) -> None:
    """Refuse une source absente sans modifier le code de sortie historique."""
    if directory is None and department is None:
        typer.echo(
            "Erreur : fournir un répertoire ou utiliser l'option --departement/-d.",
            err=True,
        )
        raise typer.Exit(1)
