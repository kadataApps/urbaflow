from pathlib import Path

from flows.cadastre.tasks.format_dgfip_topo import (
    create_dgfip_topo_tables,
    format_dgfip_topo_data,
)
from flows.cadastre.tasks.import_dgfip_topo import (
    SOURCE_FILENAME,
    import_dgfip_topo_file,
)
from prefect import flow
from shared_tasks.config import QUERIES_DIR, TEMP_DIR
from shared_tasks.etl_file_utils import download_file
from shared_tasks.file_utils import copy_directory
from shared_tasks.logging_config import get_logger

DEFAULT_SOURCE_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/906e5bd0-8be8-4150-9956-594fa0e8154c"
)


@flow
def import_dgfip_topo_flow(path: Path | None = None):
    """Importe les entités topographiques DGFiP dans la base de données."""
    logger = get_logger(__name__)
    logger.info("Démarrage du flux d'import des entités topographiques DGFiP")

    if path is None:
        path = TEMP_DIR / "dgfip_topo"
        download_file(url=DEFAULT_SOURCE_URL, target_path=path / SOURCE_FILENAME)

    queries_dir = QUERIES_DIR / "dgfip_topo"
    queries_dest_dir = TEMP_DIR / "sql"
    copy_directory(queries_dir, queries_dest_dir)

    import_dgfip_topo_file(source_dir=path)
    create_dgfip_topo_tables()
    format_dgfip_topo_data()
