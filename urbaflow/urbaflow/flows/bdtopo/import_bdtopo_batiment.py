"""
Téléchargement et import des données bâti de la BD TOPO® de l'IGN.

Les données sont téléchargées depuis la Géoplateforme (data.geopf.fr) sous forme
d'archives départementales au format GeoPackage, puis la couche `batiment` est
importée dans PostGIS.

Le périmètre d'import est défini par :
- un ou plusieurs départements (`departements`),
- un EPCI désigné par son numéro SIREN (`epci`),
- ou une liste de codes INSEE de communes (`communes`).

À chaque import, les données déjà présentes sur le périmètre sont supprimées
avant l'insertion des nouvelles données (même code département pour un import
départemental, mêmes codes INSEE pour un import EPCI ou par communes).

La couche `commune` de la livraison est utilisée pour rattacher chaque bâtiment
à sa commune (et donc à son département) par jointure spatiale.
"""

import shutil
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

import geopandas as gpd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_file_utils import download_file, extract_7z_members
from shared_tasks.etl_ogr_utils import import_vector_layer
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

logger = get_logger(__name__)

# API de téléchargement de la Géoplateforme IGN
# https://data.geopf.fr/telechargement/capabilities
GEOPF_RESOURCE_URL = "https://data.geopf.fr/telechargement/resource/BDTOPO"
GEOPF_ARCHIVE_FORMAT = "GPKG"

# API Découpage administratif (Etalab)
GEO_API_COMMUNES_URL = "https://geo.api.gouv.fr/communes"

ATOM_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "gpf_dl": "https://data.geopf.fr/annexes/ressources/xsd/gpf_dl.xsd",
}

BATIMENT_LAYER = "batiment"
COMMUNE_LAYER = "commune"

DEFAULT_TABLE_NAME = "bdtopo_batiment"
STAGING_BATIMENT_TABLE_PREFIX = "bdtopo_batiment_staging"
STAGING_COMMUNE_TABLE_PREFIX = "bdtopo_commune_staging"

BDTOPO_DOWNLOAD_DIR = Path(TEMP_DIR) / "bdtopo"

# Correspondance entre les champs de la couche `batiment` de la BD TOPO
# et les colonnes de la table cible. Les champs absents de l'édition
# téléchargée sont simplement ignorés.
BATIMENT_COLUMNS_MAPPING = {
    "cleabs": "cleabs",
    "nature": "nature",
    "usage_1": "usage1",
    "usage_2": "usage2",
    "construction_legere": "construction_legere",
    "etat_de_l_objet": "etat",
    "date_creation": "date_creation",
    "date_modification": "date_modification",
    "date_d_apparition": "date_apparition",
    "nombre_de_logements": "nb_logements",
    "nombre_d_etages": "nb_etages",
    "materiaux_des_murs": "materiaux_murs",
    "materiaux_de_la_toiture": "materiaux_toiture",
    "hauteur": "hauteur",
    "altitude_minimale_sol": "altitude_minimale_sol",
    "altitude_minimale_toit": "altitude_minimale_toit",
    "altitude_maximale_sol": "altitude_maximale_sol",
    "altitude_maximale_toit": "altitude_maximale_toit",
    "origine_du_batiment": "origine_batiment",
    "appariement_fichiers_fonciers": "appariement_fichiers_fonciers",
    "identifiants_rnb": "identifiants_rnb",
}

TARGET_TABLE_COLUMNS = """
    id bigserial PRIMARY KEY,
    cleabs text,
    code_insee text,
    code_departement text,
    nature text,
    usage1 text,
    usage2 text,
    construction_legere boolean,
    etat text,
    date_creation timestamptz,
    date_modification timestamptz,
    date_apparition date,
    nb_logements integer,
    nb_etages integer,
    materiaux_murs text,
    materiaux_toiture text,
    hauteur double precision,
    altitude_minimale_sol double precision,
    altitude_minimale_toit double precision,
    altitude_maximale_sol double precision,
    altitude_maximale_toit double precision,
    origine_batiment text,
    appariement_fichiers_fonciers text,
    identifiants_rnb text,
    millesime date,
    geom geometry(MultiPolygon, 2154)
"""


class Perimeter(NamedTuple):
    """
    Périmètre d'import.

    Attributes:
        departments: codes des départements à télécharger.
        insee_codes: codes INSEE des communes à conserver. Si None, l'intégralité
            des départements est importée.
    """

    departments: tuple[str, ...]
    insee_codes: tuple[str, ...] | None


class BdtopoResource(NamedTuple):
    """Archive BD TOPO départementale disponible au téléchargement."""

    name: str
    edition_date: str
    download_url: str


class StagingTables(NamedTuple):
    """
    Tables de travail d'une exécution d'import.

    Leur nom est unique pour chaque exécution afin que plusieurs imports
    simultanés ne se perturbent pas mutuellement.
    """

    schema: str
    batiment: str
    commune: str


def build_staging_tables(schema: str) -> StagingTables:
    """
    Construit des noms de tables de travail uniques pour une exécution d'import.
    """
    run_suffix = uuid4().hex[:8]
    return StagingTables(
        schema=schema,
        batiment=f"{STAGING_BATIMENT_TABLE_PREFIX}_{run_suffix}",
        commune=f"{STAGING_COMMUNE_TABLE_PREFIX}_{run_suffix}",
    )


def normalize_department_code(code: str) -> str:
    """
    Normalise un code de département ('1' -> '01', '2a' -> '2A', '974' -> '974').
    """
    normalized = str(code).strip().upper()
    if not normalized:
        raise ValueError("Le code de département ne peut pas être vide.")
    if len(normalized) == 1:
        return f"0{normalized}"
    return normalized


def normalize_insee_code(code: str) -> str:
    """
    Normalise un code INSEE de commune sur 5 caractères ('1001' -> '01001').
    """
    normalized = str(code).strip().upper()
    if not normalized:
        raise ValueError("Le code INSEE ne peut pas être vide.")
    return normalized.zfill(5)


def department_from_insee_code(insee_code: str) -> str:
    """
    Déduit le code du département à partir d'un code INSEE de commune.

    Gère les cas particuliers de la Corse ('2A', '2B') et des départements
    et régions d'outre-mer (codes sur 3 chiffres).
    """
    normalized = normalize_insee_code(insee_code)
    if normalized.startswith(("2A", "2B")):
        return normalized[:2]
    if normalized.startswith(("97", "98")):
        return normalized[:3]
    return normalized[:2]


def geopf_zone_code(department: str) -> str:
    """
    Convertit un code de département en code de zone Géoplateforme ('35' -> 'D035').
    """
    return f"D{normalize_department_code(department).zfill(3)}"


def split_codes(codes: str | list[str] | None) -> tuple[str, ...]:
    """
    Découpe une liste de codes fournie en ligne de commande (séparés par des
    virgules ou des espaces) en un tuple de codes.
    """
    if not codes:
        return ()
    if isinstance(codes, str):
        codes = codes.replace(";", ",").replace(" ", ",").split(",")
    return tuple(code.strip() for code in codes if str(code).strip())


@task
def fetch_epci_communes(siren_epci: str) -> list[dict]:
    """
    Récupère les communes d'un EPCI via l'API Découpage administratif.
    """
    siren_epci = str(siren_epci).strip()
    response = requests.get(
        GEO_API_COMMUNES_URL,
        params={"codeEpci": siren_epci, "fields": "code,nom,codeDepartement"},
        timeout=30,
    )
    response.raise_for_status()
    communes = response.json()
    if not communes:
        raise ValueError(
            f"Aucune commune trouvée pour l'EPCI de SIREN {siren_epci}. "
            "Vérifier le numéro SIREN fourni."
        )
    logger.info("EPCI %s : %d commune(s) trouvée(s)", siren_epci, len(communes))
    return communes


def resolve_perimeter(
    departements: str | None = None,
    epci: str | None = None,
    communes: str | None = None,
) -> Perimeter:
    """
    Détermine le périmètre d'import à partir des options de la ligne de commande.

    Exactement une des trois options doit être renseignée.
    """
    provided_options = [option for option in (departements, epci, communes) if option]
    if len(provided_options) != 1:
        raise ValueError(
            "Un seul périmètre doit être fourni : --departement, --epci ou --communes."
        )

    if departements:
        department_codes = tuple(
            dict.fromkeys(
                normalize_department_code(code) for code in split_codes(departements)
            )
        )
        logger.info("Périmètre : département(s) %s", ", ".join(department_codes))
        return Perimeter(departments=department_codes, insee_codes=None)

    if epci:
        epci_communes = fetch_epci_communes(epci)
        insee_codes = tuple(
            dict.fromkeys(
                normalize_insee_code(commune["code"]) for commune in epci_communes
            )
        )
    else:
        insee_codes = tuple(
            dict.fromkeys(normalize_insee_code(code) for code in split_codes(communes))
        )

    department_codes = tuple(
        dict.fromkeys(department_from_insee_code(code) for code in insee_codes)
    )
    logger.info(
        "Périmètre : %d commune(s) sur le(s) département(s) %s",
        len(insee_codes),
        ", ".join(department_codes),
    )
    return Perimeter(departments=department_codes, insee_codes=insee_codes)


def insee_codes_of_department(perimeter: Perimeter, department: str) -> tuple[str, ...]:
    """
    Retourne les codes INSEE du périmètre appartenant au département donné.
    """
    if perimeter.insee_codes is None:
        return ()
    return tuple(
        code
        for code in perimeter.insee_codes
        if department_from_insee_code(code) == department
    )


def _iter_atom_entries(url: str, params: dict) -> list[ElementTree.Element]:
    """
    Parcourt l'ensemble des pages d'un flux ATOM de la Géoplateforme et retourne
    les entrées rencontrées.
    """
    entries: list[ElementTree.Element] = []
    page = 1
    while True:
        response = requests.get(url, params={**params, "page": page}, timeout=60)
        response.raise_for_status()
        feed = ElementTree.fromstring(response.content)
        entries.extend(feed.findall("atom:entry", ATOM_NAMESPACES))
        page_count = int(
            feed.attrib.get(f"{{{ATOM_NAMESPACES['gpf_dl']}}}pagecount", "1")
        )
        if page >= page_count:
            return entries
        page += 1


@task
def find_bdtopo_resource(
    department: str, edition_date: str | None = None
) -> BdtopoResource:
    """
    Recherche l'archive BD TOPO d'un département sur la Géoplateforme.

    Args:
        department: code du département.
        edition_date: millésime souhaité ('2026-06-15'). Si None, la dernière
            édition disponible est retenue.
    """
    zone = geopf_zone_code(department)
    entries = _iter_atom_entries(
        GEOPF_RESOURCE_URL, {"zone": zone, "format": GEOPF_ARCHIVE_FORMAT}
    )

    editions = [
        (
            entry.findtext("atom:title", default="", namespaces=ATOM_NAMESPACES),
            entry.findtext(
                "gpf_dl:editionDate", default="", namespaces=ATOM_NAMESPACES
            ),
        )
        for entry in entries
        if entry.findtext("gpf_dl:editionDate", namespaces=ATOM_NAMESPACES)
    ]
    if not editions:
        raise ValueError(
            f"Aucune archive BD TOPO {GEOPF_ARCHIVE_FORMAT} disponible "
            f"pour la zone {zone}."
        )

    if edition_date:
        matching = [edition for edition in editions if edition[1] == edition_date]
        if not matching:
            available = ", ".join(sorted(edition[1] for edition in editions))
            raise ValueError(
                f"Millésime {edition_date} indisponible pour la zone {zone}. "
                f"Millésimes disponibles : {available}"
            )
        name, selected_edition_date = matching[0]
    else:
        name, selected_edition_date = max(editions, key=lambda edition: edition[1])

    download_url = _find_archive_download_url(name)
    logger.info("Archive BD TOPO retenue pour le département %s : %s", department, name)
    return BdtopoResource(
        name=name, edition_date=selected_edition_date, download_url=download_url
    )


def _find_archive_download_url(resource_name: str) -> str:
    """
    Retourne l'URL de l'archive .7z correspondant à une livraison BD TOPO.
    """
    response = requests.get(f"{GEOPF_RESOURCE_URL}/{resource_name}", timeout=60)
    response.raise_for_status()
    feed = ElementTree.fromstring(response.content)

    for entry in feed.findall("atom:entry", ATOM_NAMESPACES):
        for link in entry.findall("atom:link", ATOM_NAMESPACES):
            href = link.attrib.get("href", "")
            if href.endswith(".7z"):
                return href
    raise ValueError(f"Aucun lien de téléchargement trouvé pour {resource_name}")


@task
def download_and_extract_geopackage(resource: BdtopoResource) -> Path:
    """
    Télécharge l'archive BD TOPO et en extrait uniquement le GeoPackage.
    """
    archive_path = BDTOPO_DOWNLOAD_DIR / f"{resource.name}.7z"
    download_file(url=resource.download_url, target_path=archive_path)

    extracted_files = extract_7z_members(
        archive_path=archive_path,
        extract_to_path=BDTOPO_DOWNLOAD_DIR / resource.name,
        members_regex=r"\.gpkg$",
    )
    geopackage_path = extracted_files[0]
    logger.info("GeoPackage BD TOPO extrait : %s", geopackage_path)
    return geopackage_path


def read_communes_extent(
    geopackage_path: Path, insee_codes: tuple[str, ...]
) -> tuple[float, float, float, float]:
    """
    Calcule l'emprise des communes sélectionnées dans le GeoPackage BD TOPO.

    Cette emprise permet de limiter la lecture de la couche `batiment` à la zone
    utile lors de l'import.
    """
    communes = gpd.read_file(geopackage_path, layer=COMMUNE_LAYER)
    selected_communes = communes[communes["code_insee"].isin(insee_codes)]
    missing_codes = sorted(set(insee_codes) - set(selected_communes["code_insee"]))
    if missing_codes:
        logger.warning(
            "Communes absentes de l'archive BD TOPO : %s", ", ".join(missing_codes)
        )
    if selected_communes.empty:
        raise ValueError(
            "Aucune des communes demandées n'est présente dans l'archive BD TOPO."
        )
    xmin, ymin, xmax, ymax = selected_communes.total_bounds
    return (float(xmin), float(ymin), float(xmax), float(ymax))


@task
def load_staging_tables(
    geopackage_path: Path,
    staging_tables: StagingTables,
    department: str,
    insee_codes: tuple[str, ...],
) -> None:
    """
    Charge les couches `commune` et `batiment` du GeoPackage dans des tables
    temporaires de travail.

    Les livraisons départementales de la BD TOPO débordent sur les communes
    limitrophes des départements voisins : la couche `commune` est donc toujours
    filtrée sur le périmètre demandé, ce qui garantit que seuls les bâtiments de
    ce périmètre seront rattachés à une commune lors de l'insertion.
    """
    spatial_extent = None
    if insee_codes:
        quoted_codes = ", ".join(f"'{code}'" for code in insee_codes)
        commune_filter = f"code_insee IN ({quoted_codes})"
        spatial_extent = read_communes_extent(geopackage_path, insee_codes)
        logger.info("Emprise de lecture des bâtiments : %s", spatial_extent)
    else:
        commune_filter = f"code_insee_du_departement = '{department}'"

    logger.info("Import de la couche %s dans %s", COMMUNE_LAYER, staging_tables.commune)
    import_vector_layer(
        file=str(geopackage_path),
        layer=COMMUNE_LAYER,
        table=staging_tables.commune,
        schema=staging_tables.schema,
        replace=True,
        force_2d=True,
        where=commune_filter,
    )

    logger.info(
        "Import de la couche %s dans %s", BATIMENT_LAYER, staging_tables.batiment
    )
    import_vector_layer(
        file=str(geopackage_path),
        layer=BATIMENT_LAYER,
        table=staging_tables.batiment,
        schema=staging_tables.schema,
        replace=True,
        force_2d=True,
        spatial_extent=spatial_extent,
    )

    engine = create_engine()
    with engine.begin() as connection:
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
                ANALYZE {schema}.{quote(staging_tables.batiment)};
                """
            )
        )


@task
def create_bdtopo_batiment_table(
    schema: str = "public",
    table_name: str = DEFAULT_TABLE_NAME,
    recreate: bool = False,
) -> None:
    """
    Crée la table cible des bâtiments BD TOPO et ses index si elle n'existe pas.
    """
    engine = create_engine()
    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        if recreate:
            logger.warning("Suppression de la table %s.%s", schema, table_name)
            connection.execute(
                DDL(f"DROP TABLE IF EXISTS {quote(schema)}.{quote(table_name)}")
            )
        connection.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {quote(schema)}.{quote(table_name)} (
                    {TARGET_TABLE_COLUMNS}
                );
                CREATE INDEX IF NOT EXISTS {quote(f"idx_{table_name}_code_insee")}
                    ON {quote(schema)}.{quote(table_name)} (code_insee);
                CREATE INDEX IF NOT EXISTS
                    {quote(f"idx_{table_name}_code_departement")}
                    ON {quote(schema)}.{quote(table_name)} (code_departement);
                CREATE INDEX IF NOT EXISTS {quote(f"idx_{table_name}_cleabs")}
                    ON {quote(schema)}.{quote(table_name)} (cleabs);
                CREATE INDEX IF NOT EXISTS {quote(f"sidx_{table_name}_geom")}
                    ON {quote(schema)}.{quote(table_name)} USING GIST (geom);
                """
            )
        )
        logger.info("Table cible disponible : %s.%s", schema, table_name)


def _staging_columns(connection, staging_tables: StagingTables) -> set[str]:
    """
    Retourne les colonnes présentes dans la table de travail des bâtiments.
    """
    result = connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            """
        ),
        {"schema": staging_tables.schema, "table": staging_tables.batiment},
    )
    return {row[0] for row in result}


@task
def replace_perimeter_data(
    department: str,
    insee_codes: tuple[str, ...],
    edition_date: str,
    staging_tables: StagingTables,
    schema: str = "public",
    table_name: str = DEFAULT_TABLE_NAME,
) -> int:
    """
    Remplace, dans une même transaction, les bâtiments déjà présents sur le
    périmètre par les données fraîchement téléchargées.

    La suppression porte sur le code département lorsque l'import couvre le
    département entier. Dans le cas contraire, elle porte sur les communes
    effectivement chargées dans la table de travail : une commune demandée mais
    absente de la BD TOPO conserve ainsi ses données précédentes plutôt que de
    les perdre sans pouvoir les réimporter.

    Returns:
        int: le nombre de bâtiments insérés.
    """
    engine = create_engine()
    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        target_table = f"{quote(schema)}.{quote(table_name)}"
        staging_batiment = (
            f"{quote(staging_tables.schema)}.{quote(staging_tables.batiment)}"
        )
        staging_commune = (
            f"{quote(staging_tables.schema)}.{quote(staging_tables.commune)}"
        )

        if insee_codes:
            delete_statement = text(
                f"""
                DELETE FROM {target_table}
                WHERE code_insee IN (SELECT code_insee FROM {staging_commune})
                """
            )
            delete_params = {}
            perimeter_label = f"{len(insee_codes)} commune(s)"
        else:
            delete_statement = text(
                f"DELETE FROM {target_table} WHERE code_departement = :department"
            )
            delete_params = {"department": department}
            perimeter_label = f"département {department}"

        deleted_count = connection.execute(delete_statement, delete_params).rowcount
        logger.info(
            "%d bâtiment(s) supprimé(s) sur le périmètre : %s",
            deleted_count,
            perimeter_label,
        )

        available_columns = _staging_columns(connection, staging_tables)
        mapped_columns = {
            source: target
            for source, target in BATIMENT_COLUMNS_MAPPING.items()
            if source in available_columns
        }
        ignored_columns = set(BATIMENT_COLUMNS_MAPPING) - set(mapped_columns)
        if ignored_columns:
            logger.warning(
                "Champs absents de cette édition de la BD TOPO : %s",
                ", ".join(sorted(ignored_columns)),
            )

        target_columns = ", ".join(
            [
                *mapped_columns.values(),
                "code_insee",
                "code_departement",
                "millesime",
                "geom",
            ]
        )
        source_columns = ", ".join(
            f"batiment.{quote(source)}" for source in mapped_columns
        )
        insert_statement = text(
            f"""
            INSERT INTO {target_table} ({target_columns})
            SELECT
                {source_columns},
                commune.code_insee,
                COALESCE(commune.code_insee_du_departement, :department),
                :edition_date::date,
                ST_Multi(batiment.geom)
            FROM {staging_batiment} AS batiment
            INNER JOIN {staging_commune} AS commune
                ON ST_Intersects(commune.geom, ST_PointOnSurface(batiment.geom))
            """
        )
        inserted_count = connection.execute(
            insert_statement,
            {"edition_date": edition_date, "department": department},
        ).rowcount
        logger.info(
            "%d bâtiment(s) inséré(s) dans %s.%s", inserted_count, schema, table_name
        )
    return inserted_count


@task
def drop_staging_tables(staging_tables: StagingTables) -> None:
    """
    Supprime les tables de travail utilisées pendant l'import.
    """
    engine = create_engine()
    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        schema = quote(staging_tables.schema)
        connection.execute(
            DDL(
                f"""
                DROP TABLE IF EXISTS {schema}.{quote(staging_tables.batiment)};
                DROP TABLE IF EXISTS {schema}.{quote(staging_tables.commune)};
                """
            )
        )


@task
def cleanup_downloaded_files(resource: BdtopoResource) -> None:
    """
    Supprime l'archive téléchargée et le GeoPackage extrait.
    """
    archive_path = BDTOPO_DOWNLOAD_DIR / f"{resource.name}.7z"
    extract_path = BDTOPO_DOWNLOAD_DIR / resource.name
    archive_path.unlink(missing_ok=True)
    shutil.rmtree(extract_path, ignore_errors=True)
    logger.info("Fichiers temporaires supprimés pour %s", resource.name)


@flow(name="import-bdtopo-batiment")
def import_bdtopo_batiment_flow(
    departements: str | None = None,
    epci: str | None = None,
    communes: str | None = None,
    edition_date: str | None = None,
    db_schema: str = "public",
    staging_schema: str | None = None,
    table_name: str = DEFAULT_TABLE_NAME,
    recreate: bool = False,
    keep_files: bool = False,
) -> None:
    """
    Flow d'import des bâtiments de la BD TOPO® IGN sur un périmètre donné.

    Args:
        departements: codes de département séparés par des virgules ('35' ou '35,22').
        epci: numéro SIREN de l'EPCI dont les communes doivent être importées.
        communes: codes INSEE de communes séparés par des virgules.
        edition_date: millésime BD TOPO souhaité ('2026-06-15'). Par défaut, la
            dernière édition disponible.
        db_schema: schéma de la table cible.
        staging_schema: schéma des tables de travail.
            Par défaut, identique à `db_schema`.
        table_name: nom de la table cible.
        recreate: si True, la table cible est supprimée puis recréée avant l'import.
        keep_files: si True, l'archive téléchargée et le GeoPackage sont conservés.
    """
    perimeter = resolve_perimeter(
        departements=departements, epci=epci, communes=communes
    )
    staging_schema = staging_schema or db_schema

    create_bdtopo_batiment_table(
        schema=db_schema, table_name=table_name, recreate=recreate
    )

    total_inserted = 0
    for department in perimeter.departments:
        logger.info("Traitement du département %s", department)
        department_insee_codes = insee_codes_of_department(perimeter, department)
        resource = find_bdtopo_resource(
            department=department, edition_date=edition_date
        )
        geopackage_path = download_and_extract_geopackage(resource)
        staging_tables = build_staging_tables(schema=staging_schema)
        try:
            load_staging_tables(
                geopackage_path=geopackage_path,
                staging_tables=staging_tables,
                department=department,
                insee_codes=department_insee_codes,
            )
            total_inserted += replace_perimeter_data(
                department=department,
                insee_codes=department_insee_codes,
                edition_date=resource.edition_date,
                staging_tables=staging_tables,
                schema=db_schema,
                table_name=table_name,
            )
        finally:
            drop_staging_tables(staging_tables=staging_tables)
            if not keep_files:
                cleanup_downloaded_files(resource)

    logger.info(
        "Import BD TOPO bâti terminé : %d bâtiment(s) dans %s.%s",
        total_inserted,
        db_schema,
        table_name,
    )
