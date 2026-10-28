import typer
from flows.base_functions import install_base_functions_flow

app = typer.Typer()


@app.command(name="install-base-functions")
def install_base_functions() -> None:
    """Installe PolygonalMakeValid et PolygonalIntersection dans PostGIS."""
    install_base_functions_flow()
