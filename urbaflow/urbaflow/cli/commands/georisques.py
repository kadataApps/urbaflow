from pathlib import Path

import typer
from cli.options import (
    DEPARTMENT_OPTION,
    RECREATE_FALSE_OPTION,
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.georisques.import_casias import import_risques_casias_flow
from flows.georisques.import_cavite import import_risques_cavite_flow
from flows.georisques.import_gaspar import import_risques_gaspar_flow
from flows.georisques.import_icpe import import_icpe_flow
from flows.georisques.import_irep import import_risques_irep_flow
from flows.georisques.import_mvt import import_risques_mvt_flow
from flows.georisques.import_remnappes import import_remnappes_flow
from flows.georisques.import_rga import import_rga_flow
from flows.georisques.import_sis import import_risques_sis_flow
from flows.georisques.import_sup import import_risques_sup_flow
from flows.georisques.import_tri import import_tri_flow

app = typer.Typer()

OPTIONAL_DIRNAME_CAVITE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help="Répertoire des fichiers CSV. Optionnel si --departement est fourni.",
)

OPTIONAL_DIRNAME_RGA_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing RGA shapefiles. "
        "Optional if --departement is provided."
    ),
)

OPTIONAL_DIRNAME_REMNAPPES_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing REMNAPPES shapefiles. "
        "Optional if --departement is provided."
    ),
)

OPTIONAL_DIRNAME_MVT_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing MVT CSV files. "
        "Optional if --departement is provided."
    ),
)

OPTIONAL_DIRNAME_CASIAS_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing CASIAS CSV files. "
        "Optional if --departement is provided."
    ),
)

OPTIONAL_DIRNAME_SIS_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing SIS JSON files. "
        "Optional if --departement is provided."
    ),
)

OPTIONAL_DIRNAME_SUP_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing SUP JSON files. "
        "Optional if --departement is provided."
    ),
)

OPTIONAL_DIRNAME_TRI_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing TRI shapefiles. "
        "Optional if --departement is provided."
    ),
)

OPTIONAL_DIRNAME_ICPE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing ICPE shapefiles. "
        "Optional (downloads national base if omitted)."
    ),
)

OPTIONAL_DIRNAME_IREP_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing IREP CSV files. "
        "Optional (downloads national zip for --year if omitted)."
    ),
)

OPTIONAL_DIRNAME_GASPAR_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing GASPAR CSV files. "
        "Optional (downloads national zip if omitted)."
    ),
)

YEAR_IREP_OPTION = typer.Option(2024, help="Year of the IREP dataset (e.g. 2024)")

RISQUES_CAVITE_TABLE_OPTION = typer.Option("risques_cavite", help="Database table name")

RISQUES_REMNAPPES_TABLE_OPTION = typer.Option(
    "risques_remnappes", help="Database table name"
)

RISQUES_MVT_TABLE_OPTION = typer.Option("risques_mvt", help="Database table name")

RISQUES_CASIAS_TABLE_OPTION = typer.Option("risques_casias", help="Database table name")

RISQUES_SIS_TABLE_OPTION = typer.Option("risques_sis", help="Database table name")

RISQUES_SUP_TABLE_OPTION = typer.Option("risques_sup", help="Database table name")

RISQUES_TRI_TABLE_OPTION = typer.Option("risques_tri", help="Database table name")

RISQUES_ICPE_TABLE_OPTION = typer.Option("risques_icpe", help="Database table name")

RISQUES_IREP_TABLE_OPTION = typer.Option("risques_irep", help="Database table name")

RISQUES_GASPAR_TABLE_OPTION = typer.Option("risques_gaspar", help="Database table name")


@app.command()
def risques_cavite(
    dirname: Path = OPTIONAL_DIRNAME_CAVITE_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_CAVITE_TABLE_OPTION,
):
    """
    Import des données de risques de cavités.

    DIRNAME : Chemin optionnel du répertoire contenant les fichiers CSV de cavités.
    Si non fourni, l'option --departement (-d) doit être spécifiée.
    """
    # Validate that at least one of dirname or department is provided
    if dirname is None and department is None:
        typer.echo(
            "Erreur : fournir un répertoire ou utiliser l'option --departement/-d.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_cavite_flow(
        path=dirname,
        department=department,
        recreate=recreate,
        schema=schema,
        table_name=table_name,
    )


@app.command()
def risques_rga(
    dirname: Path = OPTIONAL_DIRNAME_RGA_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données de risques de retrait-gonflement des argiles (RGA).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_rga_flow(
        dirname=dirname,
        department=department,
        schema=schema,
        replace=recreate,
    )


@app.command()
def risques_remnappes(
    dirname: Path = OPTIONAL_DIRNAME_REMNAPPES_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_REMNAPPES_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données de risques d'inondation par remontée de nappe (REMNAPPES).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_remnappes_flow(
        dirname=dirname,
        department=department,
        schema=schema,
        table=table_name,
        replace=recreate,
    )


@app.command()
def risques_mvt(
    dirname: Path = OPTIONAL_DIRNAME_MVT_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_MVT_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données de mouvements de terrain (MVT).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_mvt_flow(
        path=dirname,
        department=department,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_casias(
    dirname: Path = OPTIONAL_DIRNAME_CASIAS_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_CASIAS_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données CASIAS (Anciens Sites Industriels et Activités de Service).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_casias_flow(
        path=dirname,
        department=department,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_sis(
    dirname: Path = OPTIONAL_DIRNAME_SIS_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_SIS_TABLE_OPTION,
    db_schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données SIS (Secteurs d'Information sur les Sols).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_sis_flow(
        path=dirname,
        department=department,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_sup(
    dirname: Path = OPTIONAL_DIRNAME_SUP_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_SUP_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données SUP (Servitudes d'Utilité Publique).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_sup_flow(
        path=dirname,
        department=department,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_tri(
    dirname: Path = OPTIONAL_DIRNAME_TRI_ARGUMENT,
    department: str = DEPARTMENT_OPTION,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_TRI_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données des Territoires à Risques Important d'Inondation (TRI 2020).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_tri_flow(
        dirname=dirname,
        department=department,
        schema=db_schema,
        table=table_name,
        replace=recreate,
    )


@app.command()
def risques_icpe(
    dirname: Path = OPTIONAL_DIRNAME_ICPE_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_ICPE_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données des Installations Classées (ICPE).

    Base nationale au format shapefile (WGS84). Si le répertoire n'est pas fourni,
    les données sont téléchargées automatiquement via le WFS Géorisques.
    """
    import_icpe_flow(
        dirname=dirname,
        schema=schema,
        table=table_name,
        replace=recreate,
    )


@app.command()
def risques_irep(
    dirname: Path = OPTIONAL_DIRNAME_IREP_ARGUMENT,
    year: int = YEAR_IREP_OPTION,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_IREP_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import du Registre des Émissions Polluantes (IREP).

    Base nationale annuelle CSV. Si le répertoire n'est pas fourni, le millésime
    (par défaut 2024 via --year) est téléchargé automatiquement depuis Géorisques.
    """
    import_risques_irep_flow(
        dirname=dirname,
        year=year,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_gaspar(
    dirname: Path = OPTIONAL_DIRNAME_GASPAR_ARGUMENT,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_GASPAR_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des procédures administratives de gestion des risques (GASPAR).

    Base nationale CSV (PPRN, PPRM, PPRT, CatNat, AZI, DICRIM, TIM). Si le répertoire
    n'est pas fourni, l'archive nationale est téléchargée automatiquement.
    """
    import_risques_gaspar_flow(
        dirname=dirname,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )
