from pathlib import Path

import typer
from dotenv import load_dotenv
from flows.banatic.import_banatic_communes import import_banatic_communes_flow
from flows.bdtopo.import_bdtopo_batiment import import_bdtopo_batiment_flow
from flows.bpe.import_bpe import import_bpe_flow
from flows.cadastre.flow_cadastre import (
    STEPS_FLOW_CADASTRE,
    import_cadastre_majic_flow,
)
from flows.cadastre.flow_dgfip_topo import import_dgfip_topo_flow
from flows.cartofriches.import_cartofriches import import_cartofriches_flow
from flows.dvf.dvf import dvf_flow
from flows.geoportail.import_epci_gpu import import_epci_gpu_flow
from flows.geoportail.import_gpu_sup import import_gpu_sup_flow
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
from flows.geosirene.import_geosirene_etablissement import import_geosirene_data
from flows.locomvac import import_locomvac
from flows.lovac.import_lovac import import_lovac_flow
from flows.lovac.import_lovac_fil import import_lovac_fil_flow
from flows.mh.import_mh import import_mh_flow
from shared_tasks.logging_config import setup_logging

# Load environment variables from .env file in the root directory
load_dotenv(Path(__file__).parent.parent.parent / ".env")

setup_logging()

app = typer.Typer()

DEFAULT_DIRNAME = Path("/data/")

DIRNAME_ARGUMENT = typer.Argument(
    DEFAULT_DIRNAME,
    exists=True,
    file_okay=False,
    dir_okay=True,
    writable=True,
    readable=True,
    resolve_path=True,
)

STEPS_ARGUMENT = typer.Argument(
    None,
    help=(
        "List of steps to run (e.g., 'step1', 'step2'). "
        "If not provided, all steps are run."
    ),
)

OPTIONAL_DIRNAME_CAVITE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help="Directory path containing CSV files. Optional if --department is provided.",
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

OPTIONAL_DIRNAME_GPU_SUP_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing SUP GeoPackage files. "
        "Optional (downloads latest GPKG files from Géoportail if omitted)."
    ),
)

OPTIONAL_DIRNAME_BANATIC_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing BANATIC CSV files. "
        "Optional (downloads latest CSV files from data.gouv.fr if omitted)."
    ),
)

OPTIONAL_DIRNAME_BPE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing BPE CSV files. "
        "Optional (downloads national BPE zip if omitted)."
    ),
)

OPTIONAL_DIRNAME_MH_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing MH GeoJSON file. "
        "Optional (downloads national GeoJSON if omitted)."
    ),
)

OPTIONAL_DIRNAME_GEOSIRENE_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing GeoSirene GeoParquet file. "
        "Optional (downloads national GeoParquet if omitted)."
    ),
)

OPTIONAL_DIRNAME_CARTOFRICHES_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Directory path containing Cartofriches GeoPackage file. "
        "Optional (downloads national GeoPackage if omitted)."
    ),
)

YEAR_IREP_OPTION = typer.Option(2024, help="Year of the IREP dataset (e.g. 2024)")

SCHEMA_OPTION = typer.Option("public", help="Database schema name")
LOVAC_FIL_TABLE_OPTION = typer.Option("lovac_fil", help="Database table name")
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
BANATIC_COMMUNES_TABLE_OPTION = typer.Option(
    "banatic_communes", help="Database table name"
)
INSEE_BPE_TABLE_OPTION = typer.Option("insee_bpe", help="Database table name")
GEOSIRENE_TABLE_OPTION = typer.Option(
    "geosirene_etablissement", help="Database table name"
)
PATRIMOINE_MH_TABLE_OPTION = typer.Option(
    "patrimoine_immeubles_proteges_mh", help="Database table name"
)
FRICHES_CARTOFRICHES_TABLE_OPTION = typer.Option(
    "friches_cartofriches", help="Database table name"
)
RECURSIVE_OPTION = typer.Option(False, help="Search recursively in subdirectories")
RECREATE_TRUE_OPTION = typer.Option(True, help="Drop/recreate table if it exists")
RECREATE_FALSE_OPTION = typer.Option(False, help="Drop/recreate table if it exists")
DEPARTMENT_OPTION = typer.Option(
    None,
    "-d",
    "--department",
    help="Department code (e.g., '75' for Paris). Required if dirname is not provided.",
)
DEPARTEMENT_OPTION = typer.Option(
    None,
    "-d",
    "--departement",
    help="Department code (e.g., '75' for Paris). Required if dirname is not provided.",
)
BDTOPO_DEPARTEMENTS_OPTION = typer.Option(
    None,
    "-d",
    "--departement",
    help=(
        "Code(s) de département séparés par des virgules (ex: '35' ou '35,22'). "
        "Exclusif avec --epci et --communes."
    ),
)
BDTOPO_EPCI_OPTION = typer.Option(
    None,
    "-e",
    "--epci",
    help=(
        "Numéro SIREN de l'EPCI dont les communes doivent être importées. "
        "Exclusif avec --departement et --communes."
    ),
)
BDTOPO_COMMUNES_OPTION = typer.Option(
    None,
    "-c",
    "--communes",
    help=(
        "Codes INSEE de communes séparés par des virgules (ex: '35238,35047'). "
        "Exclusif avec --departement et --epci."
    ),
)
BDTOPO_MILLESIME_OPTION = typer.Option(
    None,
    "--millesime",
    help=(
        "Millésime BD TOPO souhaité (ex: '2026-06-15'). "
        "Par défaut, la dernière édition disponible."
    ),
)
BDTOPO_BATIMENT_TABLE_OPTION = typer.Option(
    "bdtopo_batiment", help="Database table name"
)
BDTOPO_KEEP_FILES_OPTION = typer.Option(
    False,
    "--keep-files/--no-keep-files",
    help="Conserver l'archive téléchargée et le GeoPackage extrait",
)


@app.command()
def dvf(
    departements: str,
    dirname: Path = DIRNAME_ARGUMENT,
):
    dvf_flow._run(departements, dirname)


@app.command(name="dgfip-topo")
def dgfip_topo(
    dirname: Path = DIRNAME_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant le fichier des entités topographiques DGFiP
    """
    import_dgfip_topo_flow(path=dirname)


@app.command()
def locomvac(
    dirname: Path = DIRNAME_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers LOCOMVAC
    """
    typer.echo(f"Running LocomVac flow in directory: {dirname}")
    import_locomvac(dirname)


@app.command()
def lovac(
    dirname: Path = DIRNAME_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers csv LOVAC
    """
    typer.echo(f"Running Lovac flow in directory: {dirname}")
    import_lovac_flow(dirname=dirname)


@app.command()
def lovac_fil(
    dirname: Path = DIRNAME_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = LOVAC_FIL_TABLE_OPTION,
    recursive: bool = RECURSIVE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers lovac_fil.csv

    Import des données LOVAC FIL (Locaux Vacants Commerciaux - données détaillées)
    """
    typer.echo(f"Running Lovac FIL flow in directory: {dirname}")
    typer.echo(f"Target: {schema}.{table_name}")
    typer.echo(f"Recursive search: {recursive}")
    typer.echo(f"Recreate table: {recreate}")
    result = import_lovac_fil_flow(
        dirname=dirname,
        schema=schema,
        table_name=table_name,
        recursive=recursive,
        recreate=recreate,
    )
    typer.echo(f"Import completed successfully: {result}")


@app.command()
def majic(
    dirname: Path = DIRNAME_ARGUMENT,
    steps: list[str] = STEPS_ARGUMENT,
):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers MAJIC
    """
    if steps:
        # ensure step names are valid
        for step in steps:
            if step not in STEPS_FLOW_CADASTRE.keys():
                raise typer.BadParameter(
                    f"Invalid step name '{step}'. "
                    f"Valid step names are: {STEPS_FLOW_CADASTRE.keys()}"
                )

    steps_to_process = steps if steps else STEPS_FLOW_CADASTRE.keys()

    import_cadastre_majic_flow(path=dirname, enabled_steps=steps_to_process)


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
    Si non fourni, l'option --department (-d) doit être spécifiée.
    """
    # Validate that at least one of dirname or department is provided
    if dirname is None and department is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --department (-d) option.",
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
    departement: str = DEPARTEMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données de risques de retrait-gonflement des argiles (RGA).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_rga_flow(
        dirname=dirname,
        department=departement,
        schema=schema,
        replace=recreate,
    )


@app.command()
def risques_remnappes(
    dirname: Path = OPTIONAL_DIRNAME_REMNAPPES_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
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
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_remnappes_flow(
        dirname=dirname,
        department=departement,
        schema=schema,
        table=table_name,
        replace=recreate,
    )


@app.command()
def risques_mvt(
    dirname: Path = OPTIONAL_DIRNAME_MVT_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
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
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_mvt_flow(
        path=dirname,
        department=departement,
        schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_casias(
    dirname: Path = OPTIONAL_DIRNAME_CASIAS_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
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
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_casias_flow(
        path=dirname,
        department=departement,
        schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_sis(
    dirname: Path = OPTIONAL_DIRNAME_SIS_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_SIS_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données SIS (Secteurs d'Information sur les Sols).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_sis_flow(
        path=dirname,
        department=departement,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_sup(
    dirname: Path = OPTIONAL_DIRNAME_SUP_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_SUP_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données SUP (Servitudes d'Utilité Publique).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_risques_sup_flow(
        path=dirname,
        department=departement,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_tri(
    dirname: Path = OPTIONAL_DIRNAME_TRI_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = RISQUES_TRI_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
):
    """
    Import des données des Territoires à Risques Important d'Inondation (TRI 2020).

    Si le répertoire n'est pas fourni, l'option --departement (-d) doit être spécifiée
    pour télécharger les données.
    """
    # Validate that at least one of dirname or departement is provided
    if dirname is None and departement is None:
        typer.echo(
            "Error: Either provide a dirname argument or use --departement/-d option.",
            err=True,
        )
        raise typer.Exit(1)

    import_tri_flow(
        dirname=dirname,
        department=departement,
        schema=schema,
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
    schema: str = SCHEMA_OPTION,
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
        schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def risques_gaspar(
    dirname: Path = OPTIONAL_DIRNAME_GASPAR_ARGUMENT,
    schema: str = SCHEMA_OPTION,
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
        schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command(name="gpu-sup")
def gpu_sup(
    dirname: Path = OPTIONAL_DIRNAME_GPU_SUP_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    Import des Servitudes d'Utilité Publique (SUP) du Géoportail de l'Urbanisme (GPU).

    Fichiers GeoPackage nationaux issus de l'API download-latest du Géoportail.
    Importe les tables préfixées par gp_ (gp_acte_sup, gp_servitude, etc.).
    """
    import_gpu_sup_flow(
        dirname=dirname,
        schema=schema,
        replace=recreate,
    )


@app.command(name="banatic-communes")
def banatic_communes(
    dirname: Path = OPTIONAL_DIRNAME_BANATIC_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = BANATIC_COMMUNES_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    Import de la table des communes BANATIC avec le raccordement aux EPCI FP.

    Consolide la liste des communes avec les informations de leur EPCI FP.
    Si le répertoire n'est pas fourni, le téléchargement s'effectue depuis data.gouv.fr.
    """
    epci_file = dirname / "epci_fp.csv" if dirname else None
    communes_file = dirname / "communes_siren.csv" if dirname else None

    import_banatic_communes_flow(
        epci_fp_file=epci_file,
        communes_siren_file=communes_file,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command(name="bdtopo-batiment")
def bdtopo_batiment(
    departement: str = BDTOPO_DEPARTEMENTS_OPTION,
    epci: str = BDTOPO_EPCI_OPTION,
    communes: str = BDTOPO_COMMUNES_OPTION,
    millesime: str = BDTOPO_MILLESIME_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = BDTOPO_BATIMENT_TABLE_OPTION,
    recreate: bool = RECREATE_FALSE_OPTION,
    keep_files: bool = BDTOPO_KEEP_FILES_OPTION,
):
    """
    Import des bâtiments de la BD TOPO® IGN depuis la Géoplateforme.

    Le périmètre est défini par un ou plusieurs départements (--departement),
    un EPCI (--epci) ou une liste de codes INSEE de communes (--communes).
    Les bâtiments déjà présents sur le périmètre sont supprimés avant l'import.
    """
    import_bdtopo_batiment_flow(
        departements=departement,
        epci=epci,
        communes=communes,
        edition_date=millesime,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
        keep_files=keep_files,
    )


@app.command(name="epci-gpu")
def epci_gpu(
    siren: str = typer.Argument(..., help="Numéro SIREN de l'EPCI (ex: 200071629)"),
    schema: str = SCHEMA_OPTION,
    banatic_table: str = BANATIC_COMMUNES_TABLE_OPTION,
):
    """
    Intégration des communes et documents GPU d'un EPCI via APICARTO.

    1. Crée la table banatic_communes_<SIREN> enrichie par /api/gpu/municipality.
    2. Interroge les API APICARTO (zone-urba, secteur-cc, prescription-*, info-*).
    3. Met à jour les tables PostGIS gpu_* en nettoyant les anciennes partitions.
    """
    import_epci_gpu_flow(
        siren_epci=siren,
        db_schema=schema,
        banatic_table=banatic_table,
    )


@app.command()
def bpe(
    dirname: Path = OPTIONAL_DIRNAME_BPE_ARGUMENT,
    departement: str = DEPARTEMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = INSEE_BPE_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    Import de la Base Permanente des Équipements (BPE / INSEE).

    Base nationale géolocalisée (équipements, commerces, santé, sports, etc.).
    Filtrable par département (-d/--departement). Si le répertoire n'est pas fourni,
    le fichier ZIP BPE est téléchargé.
    """
    import_bpe_flow(
        department=departement,
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


@app.command()
def mh(
    dirname: Path = OPTIONAL_DIRNAME_MH_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = PATRIMOINE_MH_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
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
def geosirene(
    dirname: Path = OPTIONAL_DIRNAME_GEOSIRENE_ARGUMENT,
    department: str = DEPARTEMENT_OPTION,
    schema: str = SCHEMA_OPTION,
    table_name: str = GEOSIRENE_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
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


@app.command()
def cartofriches(
    dirname: Path = OPTIONAL_DIRNAME_CARTOFRICHES_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    table_name: str = FRICHES_CARTOFRICHES_TABLE_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
):
    """
    Import des sites référencés dans Cartofriches (friches industrielles,
    commerciales, etc.).

    Base nationale GeoPackage. Si le répertoire n'est pas fourni, le fichier
    GeoPackage est téléchargé automatiquement depuis data.gouv.fr.
    """
    import_cartofriches_flow(
        dirname=dirname,
        db_schema=schema,
        table_name=table_name,
        recreate=recreate,
    )


if __name__ == "__main__":
    app()
