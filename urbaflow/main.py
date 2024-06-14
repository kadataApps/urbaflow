import typer
from pathlib import Path
import os

from flows.dvf.download_DVF_from_imported_data import flow_dvf
from flows.cadastre.flow_cadastre import flow_clean, flow_copy_transform_majic_queries, run_routines
from flows.cadastre.tasks.fantoir_import_db import create_fantoir, formatage_fantoir, truncate_fantoir_tables
from flows.cadastre.tasks.fantoir_import_file import import_fantoir_file


etapes = {
    "1": {
        "description": "Import données brutes (6 fichiers) dans 6 tables temporaires dans PostgreSQL",
        "status": True
    },"2": {
        "description": "Copie des scripts dans le répertoire temporaire (pour adaptation des scripts en fonction des paramètres d'import)",
        "status": True
    },"3": {
        "description": "Suppression des tables métiers",
        "status": True
    },"4": {
        "description": "Initialisation de la base avec tables métiers",
        "status": True
    },"5": {
        "description": "Formatage des données MAJIC",
        "status": True
    },"6": {
        "description": "Identification des communes importées via MAJIC",
        "status": True
    },"7": {
        "description": "Téléchargement et import des données cadastre (vecteurs)",
        "status": True
    },"8": {
        "description": "Fusion des données Cadastre et MAJIC",
        "status": True
    },"9": {
        "description": "Intégration des données parcelles, proprietaires, et local dans Public",
        "status": True
    },"10": {
        "description": "Téléchargement et import des données bati (vecteurs)",
        "status": True
    },"11": {
        "description": "Intégration des données bati dans Public",
        "status": True
    },"12": {
        "description": "Nettoyage des fichiers temporaires et des tables",
        "status": True
    }
}

app = typer.Typer()


@app.command()
def fantoir(dirname: Path = typer.Argument(...,
                                           exists=True,
                                           file_okay=False,
                                           dir_okay=True,
                                           writable=True,
                                           readable=True,
                                           resolve_path=True),
            import_file: bool = typer.Option(True, help='Import fantoir raw files to db in specified schema in config.ini'),
            create_tables: bool = typer.Option(True, help='create tables communes, voies'),
            empty_tables: bool = typer.Option(False, help='truncates tables communes, voies')
            ):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers FANTOIR
    """
    flow_copy_transform_majic_queries() # copy sql scripts
    if import_file is True:
        import_fantoir_file(path=dirname).startImport()
    if create_tables is True:
        create_fantoir()
    if empty_tables is True:
        truncate_fantoir_tables()
    formatage_fantoir()
    flow_clean()

@app.command()
def majic(dirname: Path = typer.Argument(...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
            resolve_path=True),
         etape1: bool = typer.Option(etapes['1']['status'], help=etapes['1']['description']),
         etape2: bool = typer.Option(etapes['2']['status'], help=etapes['2']['description']),
         etape3: bool = typer.Option(etapes['3']['status'], help=etapes['3']['description']),
         etape4: bool = typer.Option(etapes['4']['status'], help=etapes['4']['description']),
         etape5: bool = typer.Option(etapes['5']['status'], help=etapes['5']['description']),
         etape6: bool = typer.Option(etapes['6']['status'], help=etapes['6']['description']),
         etape7: bool = typer.Option(etapes['7']['status'], help=etapes['7']['description']),
         etape8: bool = typer.Option(etapes['8']['status'], help=etapes['8']['description']),
         etape9: bool = typer.Option(etapes['9']['status'], help=etapes['9']['description']),
         etape10: bool = typer.Option(etapes['10']['status'], help=etapes['10']['description']),
         etape11: bool = typer.Option(etapes['11']['status'], help=etapes['11']['description']),
         etape12: bool = typer.Option(etapes['12']['status'], help=etapes['12']['description']),
    ):
    """
    DIRNAME : Chemin du répertoire contenant les fichiers MAJIC
    """

    if dirname.is_dir():
        typer.echo(f"Using {dirname}")
        etapes_to_process = {
            "1": { "status": etape1 },
            "2": { "status": etape2 },
            "3": { "status": etape3 },
            "4": { "status": etape4 },
            "5": { "status": etape5 },
            "6": { "status": etape6 },
            "7": { "status": etape7 },
            "8": { "status": etape8 },
            "9": { "status": etape9 },
            "10": { "status": etape10 },
            "11": { "status": etape11 },
            "12": {"status": etape12},
        }
        run_routines(path=dirname, etapes=etapes_to_process)


@app.command()
def dvf(departement: str, dirname: Path = typer.Argument(...,
                                                    exists=True,
                                                    file_okay=False,
                                                    dir_okay=True,
                                                    writable=True,
                                                    readable=True,
                                                    resolve_path=True),):
    flow_dvf(departement, dirname)

if __name__ == "__main__":
    app()
