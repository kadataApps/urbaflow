from pathlib import Path

import typer
from cli.options import (
    DEPARTMENT_OPTION,
    RECREATE_FALSE_OPTION,
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from cli.validation import require_directory_or_department
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
    help=("Répertoire des shapefiles RGA. Optionnel si --departement est fourni."),
)

OPTIONAL_DIRNAME_REMNAPPES_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire des shapefiles REMNAPPES. Optionnel si --departement est fourni."
    ),
)

OPTIONAL_DIRNAME_MVT_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=("Répertoire des fichiers CSV MVT. Optionnel si --departement est fourni."),
)

OPTIONAL_DIRNAME_CASIAS_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=("Répertoire des fichiers CSV CASIAS. Optionnel si --departement est fourni."),
)

OPTIONAL_DIRNAME_SIS_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=("Répertoire des fichiers JSON SIS. Optionnel si --departement est fourni."),
)

OPTIONAL_DIRNAME_SUP_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=("Répertoire des fichiers JSON SUP. Optionnel si --departement est fourni."),
)

OPTIONAL_DIRNAME_TRI_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=("Répertoire des shapefiles TRI. Optionnel si --departement est fourni."),
)

OPTIONAL_DIRNAME_ICPE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire des shapefiles ICPE. Par défaut, la base nationale est téléchargée."
    ),
)

OPTIONAL_DIRNAME_IREP_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire des fichiers CSV IREP. "
        "Par défaut, l'archive nationale de l'année --year est téléchargée."
    ),
)

OPTIONAL_DIRNAME_GASPAR_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire des fichiers CSV GASPAR. "
        "Par défaut, l'archive nationale est téléchargée."
    ),
)

YEAR_IREP_OPTION = typer.Option(2024, help="Année du jeu de données IREP (ex. : 2024)")

RISQUES_CAVITE_TABLE_OPTION = typer.Option(
    "risques_cavite", help="Nom de la table cible"
)

RISQUES_REMNAPPES_TABLE_OPTION = typer.Option(
    "risques_remnappes", help="Nom de la table cible"
)

RISQUES_MVT_TABLE_OPTION = typer.Option("risques_mvt", help="Nom de la table cible")

RISQUES_CASIAS_TABLE_OPTION = typer.Option(
    "risques_casias", help="Nom de la table cible"
)

RISQUES_SIS_TABLE_OPTION = typer.Option("risques_sis", help="Nom de la table cible")

RISQUES_SUP_TABLE_OPTION = typer.Option("risques_sup", help="Nom de la table cible")

RISQUES_TRI_TABLE_OPTION = typer.Option("risques_tri", help="Nom de la table cible")

RISQUES_ICPE_TABLE_OPTION = typer.Option("risques_icpe", help="Nom de la table cible")

RISQUES_IREP_TABLE_OPTION = typer.Option("risques_irep", help="Nom de la table cible")

RISQUES_GASPAR_TABLE_OPTION = typer.Option(
    "risques_gaspar", help="Nom de la table cible"
)


@app.command()
def risques_cavite(
    dirname: Path | None = OPTIONAL_DIRNAME_CAVITE_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_CAVITE_TABLE_OPTION,
) -> None:
    """
    Import des données de risques de cavités.

    DIRNAME : Chemin optionnel du répertoire contenant les fichiers CSV de cavités.
    Si non fourni, l'option --departement (-d) doit être spécifiée.
    """
    require_directory_or_department(dirname, department)

    import_risques_cavite_flow(
        path=dirname,
        department=department,
        recreate=recreate,
        schema=schema,
        table_name=table_name,
    )


@app.command()
def risques_rga(
    dirname: Path | None = OPTIONAL_DIRNAME_RGA_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
    """
    Import des données de risques de retrait-gonflement des argiles (RGA).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    require_directory_or_department(dirname, department)

    import_rga_flow(
        dirname=dirname,
        department=department,
        schema=schema,
        replace=recreate,
    )


@app.command()
def risques_remnappes(
    dirname: Path | None = OPTIONAL_DIRNAME_REMNAPPES_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_REMNAPPES_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
    """
    Import des données de risques d'inondation par remontée de nappe (REMNAPPES).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    require_directory_or_department(dirname, department)

    import_remnappes_flow(
        dirname=dirname,
        department=department,
        schema=schema,
        table=table_name,
        replace=recreate,
    )


@app.command()
def risques_mvt(
    dirname: Path | None = OPTIONAL_DIRNAME_MVT_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_MVT_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
    """
    Import des données de mouvements de terrain (MVT).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    require_directory_or_department(dirname, department)

    import_risques_mvt_flow(
        path=dirname,
        department=department,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_casias(
    dirname: Path | None = OPTIONAL_DIRNAME_CASIAS_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_CASIAS_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
    """
    Import des données CASIAS (Anciens Sites Industriels et Activités de Service).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    require_directory_or_department(dirname, department)

    import_risques_casias_flow(
        path=dirname,
        department=department,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_sis(
    dirname: Path | None = OPTIONAL_DIRNAME_SIS_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_SIS_TABLE_OPTION,
    db_schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
    """
    Import des données SIS (Secteurs d'Information sur les Sols).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    require_directory_or_department(dirname, department)

    import_risques_sis_flow(
        path=dirname,
        department=department,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_sup(
    dirname: Path | None = OPTIONAL_DIRNAME_SUP_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_SUP_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
    """
    Import des données SUP (Servitudes d'Utilité Publique).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    require_directory_or_department(dirname, department)

    import_risques_sup_flow(
        path=dirname,
        department=department,
        db_schema=db_schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_tri(
    dirname: Path | None = OPTIONAL_DIRNAME_TRI_ARGUMENT,
    department: str | None = DEPARTMENT_OPTION,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_TRI_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
    """
    Import des données des Territoires à Risques Important d'Inondation (TRI 2020).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    require_directory_or_department(dirname, department)

    import_tri_flow(
        dirname=dirname,
        department=department,
        schema=db_schema,
        table=table_name,
        replace=recreate,
    )


@app.command()
def risques_icpe(
    dirname: Path | None = OPTIONAL_DIRNAME_ICPE_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_ICPE_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
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
    dirname: Path | None = OPTIONAL_DIRNAME_IREP_ARGUMENT,
    year: int = YEAR_IREP_OPTION,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_IREP_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
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
    dirname: Path | None = OPTIONAL_DIRNAME_GASPAR_ARGUMENT,
    db_schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_GASPAR_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
) -> None:
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
