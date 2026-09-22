import gzip
import io
import os
import re
import zipfile
from pathlib import Path

import requests
from shared_tasks.config import TEMP_DIR
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)

DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024


def download_and_unzip(url: str, extract_to_path: str = TEMP_DIR):
    """
    Download a zip file from a URL and unzip it to a specified directory.

    Parameters:
    url (str): The URL of the zip file to download.
    extract_to_path (str): The directory to extract the contents to.
    Defaults to the current directory.
    """
    response = requests.get(url)

    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(extract_to_path)
        logger.info(f"Successfully extracted to {os.path.abspath(extract_to_path)}")
    else:
        logger.info(f"Failed to download the file. Status code: {response.status_code}")


def download_file(
    url: str,
    target_path: str | Path,
    chunk_size: int = DOWNLOAD_CHUNK_SIZE,
    overwrite: bool = False,
) -> Path:
    """
    Télécharge un fichier en streaming (adapté aux archives volumineuses).

    Args:
        url: URL du fichier à télécharger.
        target_path: chemin du fichier de destination.
        chunk_size: taille des blocs lus, en octets.
        overwrite: si False, le téléchargement est ignoré lorsque le fichier
            existe déjà et que sa taille correspond à celle annoncée par le serveur.

    Returns:
        Path: le chemin du fichier téléchargé.
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        total_size = int(response.headers.get("Content-Length", 0))

        if (
            not overwrite
            and target_path.exists()
            and total_size
            and target_path.stat().st_size == total_size
        ):
            logger.info(
                "Fichier déjà téléchargé, téléchargement ignoré : %s", target_path
            )
            return target_path

        logger.info(
            "Téléchargement de %s vers %s (%.1f Mo)",
            url,
            target_path,
            total_size / (1024 * 1024) if total_size else 0,
        )
        downloaded_size = 0
        next_logged_percent = 10
        with open(target_path, "wb") as output_file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                output_file.write(chunk)
                downloaded_size += len(chunk)
                if total_size:
                    percent = downloaded_size * 100 / total_size
                    if percent >= next_logged_percent:
                        logger.info("Téléchargement : %.0f%%", percent)
                        next_logged_percent += 10

    logger.info("Téléchargement terminé : %s", target_path)
    return target_path


def extract_7z_members(
    archive_path: str | Path,
    extract_to_path: str | Path,
    members_regex: str | None = None,
) -> list[Path]:
    """
    Extrait tout ou partie d'une archive 7z.

    Args:
        archive_path: chemin de l'archive .7z.
        extract_to_path: répertoire de destination.
        members_regex: expression régulière appliquée aux chemins internes de
            l'archive. Si fournie, seuls les fichiers correspondants sont extraits.

    Returns:
        list[Path]: les chemins des fichiers extraits correspondant au filtre.
    """
    import py7zr

    archive_path = Path(archive_path)
    extract_to_path = Path(extract_to_path)
    extract_to_path.mkdir(parents=True, exist_ok=True)

    with py7zr.SevenZipFile(archive_path, mode="r") as archive:
        member_names = archive.getnames()
        if members_regex:
            pattern = re.compile(members_regex)
            targets = [name for name in member_names if pattern.search(name)]
            if not targets:
                raise FileNotFoundError(
                    f"Aucun fichier correspondant à '{members_regex}' "
                    f"dans l'archive {archive_path}"
                )
        else:
            targets = member_names

        already_extracted = [
            extract_to_path / target
            for target in targets
            if (extract_to_path / target).exists()
        ]
        if len(already_extracted) == len(targets):
            logger.info("Archive déjà extraite dans %s", extract_to_path)
            return sorted(already_extracted)

        logger.info(
            "Extraction de %d fichier(s) depuis %s vers %s",
            len(targets),
            archive_path,
            extract_to_path,
        )
        archive.extract(path=extract_to_path, targets=targets)

    return sorted(extract_to_path / target for target in targets)


def unzip_file_in_place(archive_path):
    # get directory where archive_path is stored
    dir_path = os.path.dirname(archive_path)
    file_root, _ = os.path.splitext(archive_path)  # split into file.ext and .gz

    src_name = archive_path
    dest_name = os.path.join(dir_path, file_root)
    with gzip.open(src_name, "rb") as infile:
        with open(dest_name, "wb") as outfile:
            for line in infile:
                outfile.write(line)


def split_csv_file(input_file: str, output_dir: str, lines_per_chunk: int) -> list[str]:
    """
    Split a large CSV file into multiple smaller chunks of specified line count.
    Returns a list of chunk file paths.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chunk_files = []
    current_chunk = 1
    current_chunk_path = os.path.join(output_dir, f"chunk_{current_chunk}.csv")
    out_f = open(current_chunk_path, "w", encoding="utf-8")
    chunk_files.append(current_chunk_path)

    with open(input_file, encoding="utf-8") as in_f:
        header = next(in_f)
        out_f.write(header)

        line_count = 0
        for line in in_f:
            out_f.write(line)
            line_count += 1
            if line_count >= lines_per_chunk:
                out_f.close()
                current_chunk += 1
                current_chunk_path = os.path.join(
                    output_dir, f"chunk_{current_chunk}.csv"
                )
                out_f = open(current_chunk_path, "w", encoding="utf-8")
                out_f.write(header)
                chunk_files.append(current_chunk_path)
                line_count = 0
    out_f.close()
    return chunk_files
