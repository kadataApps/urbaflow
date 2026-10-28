from pathlib import Path

import typer
from cli.options import (
    DIRNAME_ARGUMENT,
)
from flows.dvf.dvf import dvf_flow

app = typer.Typer()


@app.command()
def dvf(
    departements: str,
    dirname: Path = DIRNAME_ARGUMENT,
) -> None:
    """Importe les valeurs foncières des départements demandés."""
    dvf_flow._run(departements, dirname)
