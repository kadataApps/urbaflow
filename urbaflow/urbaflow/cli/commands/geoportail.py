from pathlib import Path

import typer
from cli.options import (
    BANATIC_COMMUNES_TABLE_OPTION,
    RECREATE_TRUE_OPTION,
    SCHEMA_OPTION,
)
from flows.geoportail.import_epci_gpu import import_epci_gpu_flow
from flows.geoportail.import_gpu_plu import DEFAULT_DOWNLOAD_DIR, import_gpu_plu_flow
from flows.geoportail.import_gpu_sup import import_gpu_sup_flow

app = typer.Typer()

OPTIONAL_DIRNAME_GPU_SUP_ARGUMENT = typer.Argument(
    None,
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
    help=(
        "Répertoire des fichiers GeoPackage SUP. "
        "Par défaut, les derniers fichiers GPKG du Géoportail sont téléchargés."
    ),
)

GPU_PLU_EPCI_OPTION = typer.Option(
    None,
    "-e",
    "--epci",
    help="Code SIREN de l'EPCI à importer. Exclusif avec --commune.",
)

GPU_PLU_COMMUNE_OPTION = typer.Option(
    None,
    "-c",
    "--commune",
    help="Code INSEE de la commune à importer. Exclusif avec --epci.",
)

GPU_PLU_DOWNLOAD_DIR_OPTION = typer.Option(
    None,
    "--download-dir",
    help="Répertoire de téléchargement. Par défaut : temp/geoportail/plu.",
)

GPU_PLU_KEEP_FILES_OPTION = typer.Option(
    True,
    "--keep-files/--no-keep-files",
    help="Conserver les fichiers GeoJSON téléchargés",
)


@app.command(name="gpu-sup")
def gpu_sup(
    dirname: Path | None = OPTIONAL_DIRNAME_GPU_SUP_ARGUMENT,
    schema: str = SCHEMA_OPTION,
    recreate: bool = RECREATE_TRUE_OPTION,
) -> None:
    """
    Import des Servitudes d'Utilité Publique (SUP) du Géoportail de l'Urbanisme (GPU).

    Fichiers GeoPackage nationaux issus de l'API download-latest du Géoportail.
    Importe les tables préfixées par gp_ (gp_acte_sup, gp_servitude, etc.).
    """
    import_gpu_sup_flow(
        dirname=dirname,
        db_schema=schema,
        replace=recreate,
    )


@app.command(name="epci-gpu")
def epci_gpu(
    siren: str = typer.Argument(..., help="Numéro SIREN de l'EPCI (ex: 200071629)"),
    schema: str = SCHEMA_OPTION,
    banatic_table: str = BANATIC_COMMUNES_TABLE_OPTION,
) -> None:
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


@app.command(name="gpu-plu")
def gpu_plu(
    epci: str | None = GPU_PLU_EPCI_OPTION,
    commune: str | None = GPU_PLU_COMMUNE_OPTION,
    schema: str = SCHEMA_OPTION,
    download_dir: Path | None = GPU_PLU_DOWNLOAD_DIR_OPTION,
    keep_files: bool = GPU_PLU_KEEP_FILES_OPTION,
) -> None:
    """
    Télécharge et importe cinq couches PLU du Géoportail de l'Urbanisme.

    Le périmètre est défini par un code EPCI ou un code commune. Les tables
    créées sont préfixées par urba_. Les fichiers sont conservés par défaut.
    """
    import_gpu_plu_flow(
        epci=epci,
        commune=commune,
        db_schema=schema,
        download_dir=download_dir or DEFAULT_DOWNLOAD_DIR,
        keep_files=keep_files,
    )
