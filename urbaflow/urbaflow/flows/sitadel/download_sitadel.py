from pathlib import Path
from tempfile import NamedTemporaryFile

from prefect import flow
from shared_tasks.config import TEMP_DIR
from shared_tasks.etl_file_utils import download_file
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)

DIDO_DATAFILES_URL = (
    "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles"
)

SITADEL_DATAFILES = {
    "sitadel_communes_logements_annuels.csv": "9c90a880-4ba0-49b4-b99d-d7dd6c810dd0",
    "sitadel_communes_logements_mensuels.csv": "577a8a66-4157-4787-b00a-031b61afea61",
    "sitadel_communes_locaux_annuels.csv": "7ec53671-ce6e-4179-b77d-a2fb5e07faa8",
    "sitadel_communes_locaux_mensuels.csv": "595d7249-f563-4f81-a3b8-3ddb7a4c41f4",
    "sitadel_detail_logements.csv": "8b35affb-55fc-4c1f-915b-7750f974446a",
    "sitadel_detail_locaux.csv": "f8f0700f-806c-40a7-83b1-f21cf507e7c4",
    "sitadel_detail_permis_amenager.csv": "96883f50-538b-41f9-a059-c6eb97e6a23a",
    "sitadel_detail_permis_demolir.csv": "1a9a2f0c-56fe-4e69-84a7-fbbda2121f02",
}


def download_sitadel_file(filename: str, destination_directory: Path) -> Path:
    """Télécharge un export SDES sans remplacer un ancien fichier en cas d'échec."""
    resource_id = SITADEL_DATAFILES[filename]
    destination_directory.mkdir(parents=True, exist_ok=True)
    target_path = destination_directory / filename
    with NamedTemporaryFile(
        dir=destination_directory,
        prefix=f".{filename}.",
        suffix=".part",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
    try:
        download_file(
            url=f"{DIDO_DATAFILES_URL}/{resource_id}/csv",
            target_path=temporary_path,
            overwrite=True,
        )
        if temporary_path.stat().st_size == 0:
            raise ValueError(f"Le fichier SITADEL téléchargé est vide : {filename}")
        temporary_path.replace(target_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    logger.info("Fichier SITADEL disponible : %s", target_path)
    return target_path


@flow
def download_sitadel_flow(dirname: Path | None = None) -> list[Path]:
    """Télécharge les séries communales et les autorisations détaillées SITADEL.

    Les exports CSV nationaux complets proviennent du dernier millésime SDES
    disponible dans DiDo. Chaque fichier est remplacé seulement après la fin
    de son téléchargement ; une erreur interrompt le flow sans masquer l'échec.
    """
    destination_directory = (
        Path(dirname) if dirname is not None else TEMP_DIR / "sitadel"
    )
    downloaded_paths = [
        download_sitadel_file(filename, destination_directory)
        for filename in SITADEL_DATAFILES
    ]

    logger.info(
        "Téléchargement SITADEL terminé : %d fichiers dans %s",
        len(downloaded_paths),
        destination_directory,
    )
    return downloaded_paths
