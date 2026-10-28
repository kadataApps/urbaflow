import typer
from cli.options import (
    BANATIC_COMMUNES_TABLE_OPTION,
    RECREATE_FALSE_OPTION,
    SCHEMA_OPTION,
)
from flows.docurba.import_docurba_documents import import_docurba_documents_flow

app = typer.Typer()


@app.command(name="docurba-epci")
def docurba_epci(
    siren: str = typer.Argument(..., help="Numéro SIREN de l'EPCI (ex: 200071629)"),
    schema: str = SCHEMA_OPTION,
    table_name: str = typer.Option(
        "docurba_documents_urbanisme", help="Database table name"
    ),
    banatic_table: str = BANATIC_COMMUNES_TABLE_OPTION,
    avant: str | None = typer.Option(
        None,
        "--avant",
        help="Ne prend en compte que les événements jusqu'à cette date (YYYY-MM-DD).",
    ),
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    État des documents d'urbanisme d'un EPCI et de ses communes (API Docurba).

    Les communes de l'EPCI sont lues dans la table BANATIC. La table cible
    contient une ligne par commune et une ligne pour l'EPCI avec le document
    opposable, sa date d'approbation et le document en cours d'élaboration.
    Les lignes existantes de l'EPCI sont remplacées.
    """
    import_docurba_documents_flow(
        siren_epci=siren,
        db_schema=schema,
        table_name=table_name,
        banatic_table=banatic_table,
        before_date=avant,
        recreate=recreate,
    )
