import os
from prefect import flow
from pathlib import Path

from flows.cadastre.tasks.format_fantoir import (
    create_fantoir_tables,
    format_fantoir_data,
)
from shared_tasks.file_utils import copy_directory
from shared_tasks.logging_config import get_logger
from shared_tasks.config import QUERIES_DIR, TEMP_DIR

from .tasks.import_fantoir import import_fantoir_file


@flow
def import_fantoir_flow(path: Path):
    """
    Flow to import Fantoir data into the database.
    Args:
        path (str): Path to the directory containing Fantoir files.
    """
    logger = get_logger()
    logger.info("Starting Fantoir import flow")

    fantoir_queries_dir = os.path.join(QUERIES_DIR, "fantoir")
    fantoir_queries_dest_dir = os.path.join(TEMP_DIR, "sql")
    copy_directory(fantoir_queries_dir, fantoir_queries_dest_dir)
    logger.info(
        f"Copied Fantoir SQL scripts from {fantoir_queries_dir} to {fantoir_queries_dest_dir}"
    )

    logger.info(f"Starting Fantoir import from {path}")
    import_fantoir_file(fantoir_source_dir=path)

    create_fantoir_tables()

    format_fantoir_data()
