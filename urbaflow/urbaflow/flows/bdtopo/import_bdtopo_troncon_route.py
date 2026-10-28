"""
Import des tronçons de route BD TOPO depuis les archives IGN départementales.

Les attributs IGN sont conservés sans renommage. Les routes limitrophes sont
retenues dès qu'une des deux communes riveraines appartient au département.
Les géométries entières sont importées en MultiLineString 2D (EPSG:2154).
"""

import re
import shutil
from datetime import date
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_file_utils import download_file, extract_7z_members
from shared_tasks.etl_ogr_utils import import_vector_layer
from shared_tasks.geopf_utils import (
    GeopfResource,
    find_geopf_resource,
    geopf_zone_code,
    normalize_department_code,
)
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

logger = get_logger(__name__)

ROUTE_LAYER = "troncon_de_route"
DEFAULT_TABLE_NAME = "bdtopo_troncon_de_route"
DOWNLOAD_DIR = Path(TEMP_DIR) / "bdtopo_route"


def validate_department(department: str) -> str:
    """Normalise et valide un code de département français."""
    normalized = normalize_department_code(department)
    if not re.fullmatch(
        r"(?:0[1-9]|1[0-9]|2[1-9AB]|[3-8][0-9]|9[0-5]|97[1-46])", normalized
    ):
        raise ValueError(f"Code de département invalide : {department!r}.")
    return normalized


def build_department_filter(department: str) -> str:
    """Construit le filtre des communes riveraines, y compris en Corse et DROM."""
    department = validate_department(department)
    return (
        f"(insee_commune_gauche LIKE '{department}%' "
        f"OR insee_commune_droite LIKE '{department}%')"
    )


@task
def download_route_geopackage(resource: GeopfResource, directory: Path) -> Path:
    """Télécharge l'archive IGN et extrait son unique GeoPackage."""
    archive_path = directory / f"{resource.name}.7z"
    download_file(url=resource.download_url, target_path=archive_path)
    geopackages = extract_7z_members(
        archive_path=archive_path,
        extract_to_path=directory / "extracted",
        members_regex=r"\.gpkg$",
    )
    if len(geopackages) != 1:
        raise ValueError(
            f"L'archive {resource.name} doit contenir exactement un GeoPackage, "
            f"mais {len(geopackages)} ont été trouvés."
        )
    return geopackages[0]


@task
def load_route_staging(
    geopackage_path: Path, department: str, schema: str, staging_table: str
) -> None:
    """Charge uniquement les routes du département dans une table de travail."""
    logger.info("Chargement des tronçons de route du département %s", department)
    import_vector_layer(
        file=str(geopackage_path),
        layer=ROUTE_LAYER,
        table=staging_table,
        schema=schema,
        replace=True,
        force_2d=True,
        where=build_department_filter(department),
    )


@task
def replace_department_routes(
    department: str,
    edition_date: str,
    schema: str,
    table_name: str,
    staging_table: str,
) -> int:
    """
    Crée la cible si nécessaire et remplace un département en une transaction.

    La structure attributaire est celle de la livraison IGN. Une livraison vide,
    incomplète ou incompatible avec la cible échoue sans effacer les anciennes
    données. La clé (code_departement, cleabs) autorise un tronçon limitrophe à
    figurer dans deux départements, sans doublon au sein d'un département.
    """
    department = validate_department(department)
    edition = date.fromisoformat(edition_date)
    engine = create_engine()
    try:
        with engine.begin() as connection:
            quote = connection.engine.dialect.identifier_preparer.quote
            target = f"{quote(schema)}.{quote(table_name)}"
            staging = f"{quote(schema)}.{quote(staging_table)}"
            columns = list(
                connection.execute(
                    text(
                        """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema = :schema AND table_name = :table
                        ORDER BY ordinal_position
                        """
                    ),
                    {"schema": schema, "table": staging_table},
                ).scalars()
            )
            required_columns = {
                "cleabs",
                "geom",
                "insee_commune_gauche",
                "insee_commune_droite",
            }
            missing_columns = required_columns - set(columns)
            if missing_columns:
                raise ValueError(
                    "Champs BD TOPO obligatoires absents : "
                    + ", ".join(sorted(missing_columns))
                )
            route_count = connection.execute(
                text(f"SELECT count(*) FROM {staging}")
            ).scalar_one()
            if not route_count:
                raise ValueError(
                    f"Aucun tronçon pour le département {department} : "
                    "les données existantes sont conservées."
                )
            connection.execute(
                DDL(
                    f"""
                    CREATE TABLE IF NOT EXISTS {target} (
                        LIKE {staging},
                        code_departement text NOT NULL,
                        millesime date NOT NULL,
                        PRIMARY KEY (code_departement, cleabs)
                    );
                    CREATE INDEX IF NOT EXISTS {quote(f"sidx_{table_name}_geom")}
                        ON {target} USING GIST (geom);
                    CREATE INDEX IF NOT EXISTS {quote(f"idx_{table_name}_cleabs")}
                        ON {target} (cleabs);
                    """
                )
            )
            connection.execute(
                text(f"DELETE FROM {target} WHERE code_departement = :department"),
                {"department": department},
            )
            column_names = ", ".join(quote(column) for column in columns)
            inserted_count = connection.execute(
                text(
                    f"""
                    INSERT INTO {target}
                        ({column_names}, code_departement, millesime)
                    SELECT {column_names}, :department, :edition
                    FROM {staging}
                    """
                ),
                {"department": department, "edition": edition},
            ).rowcount
            logger.info(
                "%d tronçon(s) importé(s) pour le département %s dans %s.%s",
                inserted_count,
                department,
                schema,
                table_name,
            )
        return inserted_count
    finally:
        engine.dispose()


@task
def drop_route_staging(schema: str, staging_table: str) -> None:
    """Supprime la table de travail propre à cette exécution."""
    engine = create_engine()
    try:
        with engine.begin() as connection:
            quote = connection.engine.dialect.identifier_preparer.quote
            connection.execute(
                DDL(f"DROP TABLE IF EXISTS {quote(schema)}.{quote(staging_table)}")
            )
    finally:
        engine.dispose()


@flow(name="import-bdtopo-troncon-route")
def import_bdtopo_troncon_route_flow(
    department: str,
    edition_date: str | None = None,
    db_schema: str = "public",
    table_name: str = DEFAULT_TABLE_NAME,
    keep_files: bool = False,
) -> None:
    """
    Importe les tronçons de route d'un département depuis la Géoplateforme.

    Le dernier millésime est utilisé par défaut. La connexion est configurée par
    les variables POSTGRES_*. Le schéma cible doit exister et disposer de PostGIS.
    Les fichiers et la table de travail sont isolés par exécution, puis supprimés,
    même en cas d'échec. Avec keep_files, le répertoire est conservé et journalisé.
    """
    department = validate_department(department)
    if edition_date is not None:
        date.fromisoformat(edition_date)
    resource = find_geopf_resource(
        resource_id="BDTOPO",
        zone=geopf_zone_code(department),
        archive_format="GPKG",
        edition_date=edition_date,
        exclude_name_substring="_DIFF",
    )
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    directory = Path(mkdtemp(prefix=f"{department}_", dir=DOWNLOAD_DIR))
    staging_table = f"bdtopo_route_staging_{uuid4().hex[:12]}"
    try:
        geopackage_path = download_route_geopackage(resource, directory)
        try:
            load_route_staging(geopackage_path, department, db_schema, staging_table)
            replace_department_routes(
                department=department,
                edition_date=resource.edition_date,
                schema=db_schema,
                table_name=table_name,
                staging_table=staging_table,
            )
        finally:
            drop_route_staging(db_schema, staging_table)
    finally:
        if keep_files:
            logger.info("Fichiers BD TOPO conservés dans %s", directory)
        else:
            shutil.rmtree(directory)
            logger.info("Fichiers temporaires BD TOPO supprimés : %s", directory)
