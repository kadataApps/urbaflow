"""
Téléchargement et import des données OCS GE (Occupation du Sol à Grande Échelle)
de l'IGN.

Les données sont téléchargées depuis la Géoplateforme (data.geopf.fr) sous forme
d'archives départementales au format GeoPackage. Deux couches sont importées dans
PostGIS :
- `OCCUPATION_SOL` : polygones de couverture et d'usage du sol (nomenclature CNIG),
- `ZONE_CONSTRUITE` : polygones des zones bâties.

Le périmètre d'import est défini par :
- un ou plusieurs départements (`departements`),
- un EPCI désigné par son numéro SIREN (`epci`),
- ou une liste de codes INSEE de communes (`communes`).

Les livraisons OCS GE de la Géoplateforme sont toujours départementales et
n'embarquent pas de couche communale (contrairement à la BD TOPO). Lorsque le
périmètre est restreint à un EPCI ou à une liste de communes, les contours des
communes sont donc récupérés depuis l'API Découpage administratif
(geo.api.gouv.fr) et utilisés pour ne conserver que les polygones OCS GE
intersectant le périmètre demandé. Ces contours sont simplifiés : ils suffisent à
sélectionner les polygones concernés mais ne permettent pas un découpage précis
des géométries en bordure de commune.

Seule la dernière édition complète est utilisée : les livraisons différentielles
("OCS-GE_..._DIFF-...", qui ne décrivent que les évolutions entre deux millésimes)
sont ignorées.

À chaque import, les données déjà présentes sur le périmètre sont supprimées avant
l'insertion des nouvelles données (même code département pour un import
départemental, même emprise communale pour un import EPCI ou par communes).
"""

import shutil
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

import geopandas as gpd
import requests
from prefect import flow, task
from shapely.geometry import MultiPolygon, shape
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_file_utils import download_file, extract_7z_members
from shared_tasks.etl_gpd_utils import create_table_from_geodataframe, load
from shared_tasks.etl_ogr_utils import import_vector_layer
from shared_tasks.geopf_utils import (
    GEO_API_COMMUNES_URL,
    GeopfResource,
    department_from_insee_code,
    find_geopf_resource,
    geopf_zone_code,
    insee_codes_of_department,
    resolve_perimeter,
)
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

logger = get_logger(__name__)

# Identifiant de la ressource OCS GE sur la Géoplateforme et format de livraison
GEOPF_RESOURCE_ID = "OCSGE"
GEOPF_ARCHIVE_FORMAT = "GPKG"
# Marqueur des livraisons différentielles, à exclure des éditions disponibles
DIFF_DELIVERY_MARKER = "_DIFF"

OCCUPATION_SOL_LAYER = "OCCUPATION_SOL"
ZONE_CONSTRUITE_LAYER = "ZONE_CONSTRUITE"

DEFAULT_OCCUPATION_SOL_TABLE = "ocsge_occupation_sol"
DEFAULT_ZONE_CONSTRUITE_TABLE = "ocsge_zone_construite"
STAGING_OCCUPATION_SOL_PREFIX = "ocsge_occupation_sol_staging"
STAGING_ZONE_CONSTRUITE_PREFIX = "ocsge_zone_construite_staging"
STAGING_COMMUNE_PREFIX = "ocsge_commune_staging"

OCSGE_DOWNLOAD_DIR = Path(TEMP_DIR) / "ocsge"

# Correspondance entre les champs des couches OCS GE et les colonnes des tables
# cibles. Chaque valeur est un tuple (colonne cible, expression SQL utilisée pour
# lire le champ de travail, `{col}` étant remplacé par la colonne source qualifiée).
# Les champs absents de l'édition téléchargée sont simplement ignorés.
OCCUPATION_SOL_COLUMNS_MAPPING = {
    "id": ("identifiant", "{col}"),
    "code_cs": ("code_couverture", "{col}"),
    "code_us": ("code_usage", "{col}"),
    # Le champ source est un millésime (année) stocké en texte sur 4 caractères.
    "millesime": ("annee_maj", "NULLIF({col}, '')::smallint"),
    "source": ("source", "{col}"),
    # Le champ source est un entier 0/1 indiquant l'appartenance à l'ossature.
    "ossature": ("ossature", "({col} <> 0)"),
    "id_origine": ("identifiant_origine", "{col}"),
    "code_or": ("code_origine", "{col}"),
}

# La couche `ZONE_CONSTRUITE` ne porte que peu d'attributs.
ZONE_CONSTRUITE_COLUMNS_MAPPING = {
    "id": ("identifiant", "{col}"),
    "millesime": ("annee_maj", "NULLIF({col}, '')::smallint"),
}

OCCUPATION_SOL_TABLE_COLUMNS = """
    id bigserial PRIMARY KEY,
    identifiant text,
    code_departement text,
    code_couverture text,
    code_usage text,
    annee_maj smallint,
    source text,
    ossature boolean,
    identifiant_origine text,
    code_origine text,
    millesime date,
    geom geometry(MultiPolygon, 2154)
"""

ZONE_CONSTRUITE_TABLE_COLUMNS = """
    id bigserial PRIMARY KEY,
    identifiant text,
    code_departement text,
    annee_maj smallint,
    millesime date,
    geom geometry(MultiPolygon, 2154)
"""


class StagingTables(NamedTuple):
    """
    Tables de travail d'une exécution d'import.

    Leur nom est unique pour chaque exécution afin que plusieurs imports
    simultanés ne se perturbent pas mutuellement. `commune` est absente
    (None) lorsque l'import couvre un département entier.
    """

    schema: str
    occupation_sol: str
    zone_construite: str
    commune: str | None


def build_staging_tables(schema: str, with_commune: bool) -> StagingTables:
    """
    Construit des noms de tables de travail uniques pour une exécution d'import.
    """
    run_suffix = uuid4().hex[:8]
    return StagingTables(
        schema=schema,
        occupation_sol=f"{STAGING_OCCUPATION_SOL_PREFIX}_{run_suffix}",
        zone_construite=f"{STAGING_ZONE_CONSTRUITE_PREFIX}_{run_suffix}",
        commune=f"{STAGING_COMMUNE_PREFIX}_{run_suffix}" if with_commune else None,
    )


@task
def find_ocsge_resource(
    department: str, edition_date: str | None = None
) -> GeopfResource:
    """
    Recherche la dernière archive OCS GE complète d'un département sur la
    Géoplateforme.

    Args:
        department: code du département.
        edition_date: millésime souhaité ('2023-01-01'). Si None, la dernière
            édition complète disponible est retenue.
    """
    return find_geopf_resource(
        resource_id=GEOPF_RESOURCE_ID,
        zone=geopf_zone_code(department),
        archive_format=GEOPF_ARCHIVE_FORMAT,
        edition_date=edition_date,
        exclude_name_substring=DIFF_DELIVERY_MARKER,
    )


@task
def download_and_extract_geopackages(resource: GeopfResource) -> tuple[Path, Path]:
    """
    Télécharge une livraison OCS GE et en extrait les GeoPackages
    `OCCUPATION_SOL` et `ZONE_CONSTRUITE`.
    """
    archive_path = OCSGE_DOWNLOAD_DIR / f"{resource.name}.7z"
    download_file(url=resource.download_url, target_path=archive_path)

    extracted_files = extract_7z_members(
        archive_path=archive_path,
        extract_to_path=OCSGE_DOWNLOAD_DIR / resource.name,
        members_regex=rf"({OCCUPATION_SOL_LAYER}|{ZONE_CONSTRUITE_LAYER})\.gpkg$",
    )
    occupation_sol_path = next(
        f for f in extracted_files if f.name == f"{OCCUPATION_SOL_LAYER}.gpkg"
    )
    zone_construite_path = next(
        f for f in extracted_files if f.name == f"{ZONE_CONSTRUITE_LAYER}.gpkg"
    )
    logger.info(
        "GeoPackages OCS GE extraits : %s, %s",
        occupation_sol_path,
        zone_construite_path,
    )
    return occupation_sol_path, zone_construite_path


@task
def fetch_communes_geometries(insee_codes: tuple[str, ...]) -> gpd.GeoDataFrame:
    """
    Récupère les contours des communes demandées depuis l'API Découpage
    administratif et retourne un GeoDataFrame reprojeté en Lambert-93 (EPSG:2154).

    Les contours sont récupérés département par département (un seul appel par
    département couvert par le périmètre) puis filtrés sur les codes INSEE
    demandés.
    """
    departments = sorted({department_from_insee_code(code) for code in insee_codes})
    records = []
    for department in departments:
        response = requests.get(
            GEO_API_COMMUNES_URL,
            params={"codeDepartement": department, "fields": "code,contour"},
            timeout=60,
        )
        response.raise_for_status()
        records.extend(response.json())

    contours_by_code = {
        record["code"]: record["contour"] for record in records if record.get("contour")
    }
    missing_codes = sorted(set(insee_codes) - set(contours_by_code))
    if missing_codes:
        logger.warning(
            "Contour indisponible pour les commune(s) : %s", ", ".join(missing_codes)
        )

    geometries = [
        {"code_insee": code, "geometry": shape(contours_by_code[code])}
        for code in insee_codes
        if code in contours_by_code
    ]
    if not geometries:
        raise ValueError(
            "Aucun contour de commune n'a pu être récupéré pour le périmètre demandé."
        )

    gdf = gpd.GeoDataFrame(geometries, geometry="geometry", crs="EPSG:4326")
    gdf = gdf.rename_geometry("geom")
    gdf = gdf.to_crs("EPSG:2154")
    # L'API Découpage administratif retourne des Polygon ou des MultiPolygon selon
    # les communes (îles, enclaves) : on uniformise en MultiPolygon pour que le
    # type de colonne de la table de travail soit homogène.
    gdf["geom"] = gdf["geom"].apply(
        lambda geom: geom if geom.geom_type == "MultiPolygon" else MultiPolygon([geom])
    )
    logger.info("Contours récupérés pour %d commune(s)", len(gdf))
    return gdf


@task
def load_staging_commune_table(
    communes_gdf: gpd.GeoDataFrame, staging_tables: StagingTables
) -> None:
    """
    Charge les contours communaux dans une table de travail, utilisée pour filtrer
    spatialement les polygones OCS GE sur le périmètre demandé.
    """
    engine = create_engine()
    with engine.begin() as connection:
        create_table_from_geodataframe(
            gdf=communes_gdf,
            connection=connection,
            table_name=staging_tables.commune,
            schema=staging_tables.schema,
            recreate=True,
            srs=2154,
            logger=logger,
        )
        load(
            communes_gdf,
            connection=connection,
            table_name=staging_tables.commune,
            schema=staging_tables.schema,
            how="append",
            logger=logger,
        )
        quote = connection.engine.dialect.identifier_preparer.quote
        schema = quote(staging_tables.schema)
        connection.execute(
            DDL(
                f"""
                CREATE INDEX IF NOT EXISTS
                    {quote(f"sidx_{staging_tables.commune}_geom")}
                    ON {schema}.{quote(staging_tables.commune)}
                    USING GIST (geom);
                ANALYZE {schema}.{quote(staging_tables.commune)};
                """
            )
        )


def communes_extent(
    communes_gdf: gpd.GeoDataFrame,
) -> tuple[float, float, float, float]:
    """
    Calcule l'emprise des communes sélectionnées, en EPSG:4326.

    Les livraisons OCS GE sont chacune dans un système de coordonnées propre à
    leur territoire (Lambert-93 en métropole, projections locales outre-mer) :
    l'emprise est donc calculée en EPSG:4326 et transmise à `ogr2ogr` avec ce
    même SRS (`-spat_srs`), qui se charge de la reprojeter dans le SRS de la
    couche source avant lecture.
    """
    xmin, ymin, xmax, ymax = communes_gdf.to_crs("EPSG:4326").total_bounds
    return (float(xmin), float(ymin), float(xmax), float(ymax))


@task
def load_staging_layers(
    occupation_sol_path: Path,
    zone_construite_path: Path,
    staging_tables: StagingTables,
    spatial_extent: tuple[float, float, float, float] | None,
) -> None:
    """
    Charge les couches `OCCUPATION_SOL` et `ZONE_CONSTRUITE` du GeoPackage dans
    des tables temporaires de travail.
    """
    logger.info(
        "Import de la couche %s dans %s",
        OCCUPATION_SOL_LAYER,
        staging_tables.occupation_sol,
    )
    import_vector_layer(
        file=str(occupation_sol_path),
        layer=OCCUPATION_SOL_LAYER,
        table=staging_tables.occupation_sol,
        schema=staging_tables.schema,
        replace=True,
        force_2d=True,
        spatial_extent=spatial_extent,
        spatial_extent_srs="EPSG:4326" if spatial_extent else None,
    )

    logger.info(
        "Import de la couche %s dans %s",
        ZONE_CONSTRUITE_LAYER,
        staging_tables.zone_construite,
    )
    import_vector_layer(
        file=str(zone_construite_path),
        layer=ZONE_CONSTRUITE_LAYER,
        table=staging_tables.zone_construite,
        schema=staging_tables.schema,
        replace=True,
        force_2d=True,
        spatial_extent=spatial_extent,
        spatial_extent_srs="EPSG:4326" if spatial_extent else None,
    )

    engine = create_engine()
    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        schema = quote(staging_tables.schema)
        connection.execute(
            DDL(
                f"""
                CREATE INDEX IF NOT EXISTS
                    {quote(f"sidx_{staging_tables.occupation_sol}_geom")}
                    ON {schema}.{quote(staging_tables.occupation_sol)}
                    USING GIST (geom);
                CREATE INDEX IF NOT EXISTS
                    {quote(f"sidx_{staging_tables.zone_construite}_geom")}
                    ON {schema}.{quote(staging_tables.zone_construite)}
                    USING GIST (geom);
                ANALYZE {schema}.{quote(staging_tables.occupation_sol)};
                ANALYZE {schema}.{quote(staging_tables.zone_construite)};
                """
            )
        )


@task
def create_ocsge_tables(
    schema: str = "public",
    occupation_sol_table: str = DEFAULT_OCCUPATION_SOL_TABLE,
    zone_construite_table: str = DEFAULT_ZONE_CONSTRUITE_TABLE,
    recreate: bool = False,
) -> None:
    """
    Crée les tables cibles OCS GE et leurs index si elles n'existent pas.
    """
    engine = create_engine()
    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        for table_name, table_columns in (
            (occupation_sol_table, OCCUPATION_SOL_TABLE_COLUMNS),
            (zone_construite_table, ZONE_CONSTRUITE_TABLE_COLUMNS),
        ):
            if recreate:
                logger.warning("Suppression de la table %s.%s", schema, table_name)
                connection.execute(
                    DDL(f"DROP TABLE IF EXISTS {quote(schema)}.{quote(table_name)}")
                )
            connection.execute(
                DDL(
                    f"""
                    CREATE TABLE IF NOT EXISTS {quote(schema)}.{quote(table_name)} (
                        {table_columns}
                    );
                    CREATE INDEX IF NOT EXISTS
                        {quote(f"idx_{table_name}_code_departement")}
                        ON {quote(schema)}.{quote(table_name)} (code_departement);
                    CREATE INDEX IF NOT EXISTS {quote(f"sidx_{table_name}_geom")}
                        ON {quote(schema)}.{quote(table_name)} USING GIST (geom);
                    """
                )
            )
            logger.info("Table cible disponible : %s.%s", schema, table_name)


def _staging_columns(connection, schema: str, table: str) -> set[str]:
    """
    Retourne les colonnes présentes dans une table de travail.
    """
    result = connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            """
        ),
        {"schema": schema, "table": table},
    )
    return {row[0] for row in result}


def _replace_layer_data(
    connection,
    quote,
    staging_tables: StagingTables,
    staging_table: str,
    columns_mapping: dict[str, tuple[str, str]],
    department: str,
    edition_date: str,
    schema: str,
    table_name: str,
) -> int:
    """
    Supprime puis réinsère les données d'une couche OCS GE sur le périmètre
    demandé.

    Lorsque le périmètre est restreint à des communes, la suppression et
    l'insertion portent sur les polygones intersectant les contours de travail
    (`staging_tables.commune`) ; sinon elles portent sur le département entier.
    """
    target_table = f"{quote(schema)}.{quote(table_name)}"
    staging = f"{quote(staging_tables.schema)}.{quote(staging_table)}"

    commune_predicate = ""
    delete_params = {"department": department}
    if staging_tables.commune:
        staging_commune = (
            f"{quote(staging_tables.schema)}.{quote(staging_tables.commune)}"
        )
        commune_predicate = (
            f" AND EXISTS (SELECT 1 FROM {staging_commune} AS commune "
            "WHERE ST_Intersects(commune.geom, target.geom))"
        )
        delete_statement = text(
            f"DELETE FROM {target_table} AS target "
            f"WHERE code_departement = :department{commune_predicate}"
        )
    else:
        delete_statement = text(
            f"DELETE FROM {target_table} WHERE code_departement = :department"
        )

    deleted_count = connection.execute(delete_statement, delete_params).rowcount
    logger.info(
        "%d enregistrement(s) supprimé(s) dans %s sur le périmètre demandé",
        deleted_count,
        table_name,
    )

    available_columns = _staging_columns(
        connection, staging_tables.schema, staging_table
    )
    mapped_columns = {
        source: mapping
        for source, mapping in columns_mapping.items()
        if source in available_columns
    }
    ignored_columns = set(columns_mapping) - set(mapped_columns)
    if ignored_columns:
        logger.warning(
            "Champs absents de cette édition OCS GE (%s) : %s",
            table_name,
            ", ".join(sorted(ignored_columns)),
        )

    target_columns = ", ".join(
        [
            *(target for target, _ in mapped_columns.values()),
            "code_departement",
            "millesime",
            "geom",
        ]
    )
    source_columns = ", ".join(
        expression.format(col=f"src.{quote(source)}")
        for source, (_, expression) in mapped_columns.items()
    )

    insert_where = ""
    if staging_tables.commune:
        staging_commune = (
            f"{quote(staging_tables.schema)}.{quote(staging_tables.commune)}"
        )
        insert_where = (
            f" WHERE EXISTS (SELECT 1 FROM {staging_commune} AS commune "
            "WHERE ST_Intersects(commune.geom, src.geom))"
        )

    insert_statement = text(
        f"""
        INSERT INTO {target_table} ({target_columns})
        SELECT
            {source_columns},
            :department,
            CAST(:edition_date AS date),
            ST_Multi(src.geom)
        FROM {staging} AS src
        {insert_where}
        """
    )
    inserted_count = connection.execute(
        insert_statement, {"department": department, "edition_date": edition_date}
    ).rowcount
    logger.info(
        "%d enregistrement(s) inséré(s) dans %s.%s",
        inserted_count,
        schema,
        table_name,
    )
    return inserted_count


@task
def replace_perimeter_data(
    department: str,
    edition_date: str,
    staging_tables: StagingTables,
    schema: str = "public",
    occupation_sol_table: str = DEFAULT_OCCUPATION_SOL_TABLE,
    zone_construite_table: str = DEFAULT_ZONE_CONSTRUITE_TABLE,
) -> tuple[int, int]:
    """
    Remplace, dans une même transaction, les données OCS GE déjà présentes sur le
    périmètre par les données fraîchement téléchargées.

    Returns:
        tuple[int, int]: le nombre de polygones insérés (occupation du sol,
            zones construites).
    """
    engine = create_engine()
    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        occupation_sol_count = _replace_layer_data(
            connection=connection,
            quote=quote,
            staging_tables=staging_tables,
            staging_table=staging_tables.occupation_sol,
            columns_mapping=OCCUPATION_SOL_COLUMNS_MAPPING,
            department=department,
            edition_date=edition_date,
            schema=schema,
            table_name=occupation_sol_table,
        )
        zone_construite_count = _replace_layer_data(
            connection=connection,
            quote=quote,
            staging_tables=staging_tables,
            staging_table=staging_tables.zone_construite,
            columns_mapping=ZONE_CONSTRUITE_COLUMNS_MAPPING,
            department=department,
            edition_date=edition_date,
            schema=schema,
            table_name=zone_construite_table,
        )
    return occupation_sol_count, zone_construite_count


@task
def drop_staging_tables(staging_tables: StagingTables) -> None:
    """
    Supprime les tables de travail utilisées pendant l'import.
    """
    engine = create_engine()
    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        schema = quote(staging_tables.schema)
        tables_to_drop = [staging_tables.occupation_sol, staging_tables.zone_construite]
        if staging_tables.commune:
            tables_to_drop.append(staging_tables.commune)
        statements = "\n".join(
            f"DROP TABLE IF EXISTS {schema}.{quote(table)};" for table in tables_to_drop
        )
        connection.execute(DDL(statements))


@task
def cleanup_downloaded_files(resource: GeopfResource) -> None:
    """
    Supprime l'archive téléchargée et les GeoPackages extraits.
    """
    archive_path = OCSGE_DOWNLOAD_DIR / f"{resource.name}.7z"
    extract_path = OCSGE_DOWNLOAD_DIR / resource.name
    archive_path.unlink(missing_ok=True)
    shutil.rmtree(extract_path, ignore_errors=True)
    logger.info("Fichiers temporaires supprimés pour %s", resource.name)


@flow(name="import-ocsge")
def import_ocsge_flow(
    departements: str | None = None,
    epci: str | None = None,
    communes: str | None = None,
    edition_date: str | None = None,
    db_schema: str = "public",
    staging_schema: str | None = None,
    occupation_sol_table: str = DEFAULT_OCCUPATION_SOL_TABLE,
    zone_construite_table: str = DEFAULT_ZONE_CONSTRUITE_TABLE,
    recreate: bool = False,
    keep_files: bool = False,
) -> None:
    """
    Flow d'import des données OCS GE (Occupation du Sol à Grande Échelle) de
    l'IGN sur un périmètre donné.

    Args:
        departements: codes de département séparés par des virgules ('35' ou '35,22').
        epci: numéro SIREN de l'EPCI dont les communes doivent être importées.
        communes: codes INSEE de communes séparés par des virgules.
        edition_date: millésime OCS GE souhaité ('2023-01-01'). Par défaut, la
            dernière édition complète disponible (les livraisons différentielles
            sont ignorées).
        db_schema: schéma des tables cibles.
        staging_schema: schéma des tables de travail.
            Par défaut, identique à `db_schema`.
        occupation_sol_table: nom de la table cible pour la couche `OCCUPATION_SOL`.
        zone_construite_table: nom de la table cible pour la couche `ZONE_CONSTRUITE`.
        recreate: si True, les tables cibles sont supprimées puis recréées avant
            l'import.
        keep_files: si True, l'archive téléchargée et les GeoPackages extraits sont
            conservés.
    """
    perimeter = resolve_perimeter(
        departements=departements, epci=epci, communes=communes
    )
    staging_schema = staging_schema or db_schema

    create_ocsge_tables(
        schema=db_schema,
        occupation_sol_table=occupation_sol_table,
        zone_construite_table=zone_construite_table,
        recreate=recreate,
    )

    total_occupation_sol = 0
    total_zone_construite = 0
    for department in perimeter.departments:
        logger.info("Traitement du département %s", department)
        department_insee_codes = insee_codes_of_department(perimeter, department)
        resource = find_ocsge_resource(department=department, edition_date=edition_date)
        occupation_sol_path, zone_construite_path = download_and_extract_geopackages(
            resource
        )

        staging_tables = build_staging_tables(
            schema=staging_schema, with_commune=bool(department_insee_codes)
        )
        try:
            spatial_extent = None
            if department_insee_codes:
                communes_gdf = fetch_communes_geometries(department_insee_codes)
                load_staging_commune_table(communes_gdf, staging_tables)
                spatial_extent = communes_extent(communes_gdf)
                logger.info(
                    "Emprise de lecture des polygones OCS GE : %s", spatial_extent
                )

            load_staging_layers(
                occupation_sol_path=occupation_sol_path,
                zone_construite_path=zone_construite_path,
                staging_tables=staging_tables,
                spatial_extent=spatial_extent,
            )
            occupation_sol_count, zone_construite_count = replace_perimeter_data(
                department=department,
                edition_date=resource.edition_date,
                staging_tables=staging_tables,
                schema=db_schema,
                occupation_sol_table=occupation_sol_table,
                zone_construite_table=zone_construite_table,
            )
            total_occupation_sol += occupation_sol_count
            total_zone_construite += zone_construite_count
        finally:
            drop_staging_tables(staging_tables=staging_tables)
            if not keep_files:
                cleanup_downloaded_files(resource)

    logger.info(
        "Import OCS GE terminé : %d polygone(s) d'occupation du sol et "
        "%d zone(s) construite(s) dans %s",
        total_occupation_sol,
        total_zone_construite,
        db_schema,
    )
