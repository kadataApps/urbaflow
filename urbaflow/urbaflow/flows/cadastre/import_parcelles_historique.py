"""Construction incrémentale de l'historique des parcelles cadastrales Etalab.

Chaque parcelle est stockée avec son intervalle de validité :
- ``millesime_debut`` : premier millésime dans lequel la parcelle apparaît ;
- ``millesime_fin`` : premier millésime dans lequel elle n'apparaît plus
  (``NULL`` tant qu'elle existe dans le dernier millésime importé).

La colonne générée ``periode`` (``daterange`` semi-ouvert ``[debut, fin)``)
permet de reconstituer le parcellaire d'un millésime donné :
``WHERE periode @> DATE '2022-01-01'``.
"""

import re
import tempfile
import warnings
import zipfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from io import StringIO
from pathlib import Path
from typing import NamedTuple

import duckdb
import numpy as np
import pandas as pd
import pyogrio.raw
import requests
from prefect import flow
from psycopg2.extras import execute_values
from pyproj import CRS
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_file_utils import download_file
from shared_tasks.geopf_utils import normalize_department_code, split_codes
from shared_tasks.logging_config import get_logger
from sqlalchemy import text

logger = get_logger(__name__)

ETALAB_CADASTRE_URL = "https://cadastre.data.gouv.fr/data/etalab-cadastre"
FIRST_MILLESIME = date(2018, 4, 3)
FIRST_GEOPARQUET_MILLESIME = date(2025, 4, 1)
# Millésimes publiés uniquement à la commune : non importés pour l'instant.
EXCLUDED_MILLESIMES = frozenset(
    {date(2017, 7, 6), date(2017, 10, 12), date(2018, 1, 2)}
)

HISTORY_TABLE = "dgfip_parcelle_historique"
IMPORT_LOG_TABLE = "dgfip_parcelle_historique_import"
CURRENT_VIEW = "dgfip_parcelle_actuelle"
MILLESIME_FUNCTION = "dgfip_parcelles_au_millesime"

BATCH_SIZE = 5000
# Au-delà de cette part de parcelles disparues, un avertissement est émis.
CLOSED_RATIO_WARNING = 0.1

PARCEL_COLUMNS = (
    ("id", "text"),
    ("commune", "text"),
    ("prefixe", "text"),
    ("section", "text"),
    ("numero", "text"),
    ("contenance", "bigint"),
    ("created", "date"),
    ("updated", "date"),
)
DEPARTEMENT_PATTERN = re.compile(r"(?:[0-9]{2,3}|2[AB])")
MILLESIME_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# Tuple produit par les sources : attributs de PARCEL_COLUMNS, WKB, SRID source.
ParcelRow = tuple


class ParcelSource(NamedTuple):
    """Accès aux parcelles d'un département pour un millésime donné.

    Attributes:
        read_ids: renvoie les identifiants de toutes les parcelles de la source.
        iter_rows: renvoie les lignes complètes des seuls identifiants demandés.
    """

    read_ids: Callable[[], list[str]]
    iter_rows: Callable[[set[str]], Iterator[ParcelRow]]


def is_remote(location: str) -> bool:
    """Indique si l'emplacement désigne une ressource HTTP(S)."""
    return location.startswith(("https://", "http://"))


def list_directory(base_location: str, *parts: str) -> list[str]:
    """Liste les entrées d'un répertoire Etalab, distant (index HTML) ou local."""
    location = "/".join([base_location.rstrip("/"), *parts])
    if not is_remote(location):
        return sorted(path.name for path in Path(location).iterdir())
    response = requests.get(f"{location}/", timeout=(30, 120))
    response.raise_for_status()
    names = re.findall(r'href="[^"]*?/([^/"]+)/?"', response.text)
    return sorted({name for name in names if name != ".."})


def list_available_millesimes(base_location: str) -> list[date]:
    """Renvoie les millésimes publiés, triés chronologiquement."""
    return sorted(
        date.fromisoformat(name)
        for name in list_directory(base_location)
        if MILLESIME_PATTERN.fullmatch(name)
    )


def list_departements(base_location: str, millesime: date) -> list[str]:
    """Renvoie les départements publiés en shapefile pour un millésime.

    L'arborescence shapefile départementale existe aussi pour les millésimes
    GeoParquet : elle sert de référence pour énumérer les départements.
    """
    names = list_directory(base_location, millesime.isoformat(), "shp", "departements")
    return [name for name in names if DEPARTEMENT_PATTERN.fullmatch(name)]


def parse_millesimes(millesimes: str | None) -> list[date] | None:
    """Convertit une liste de dates ISO séparées par des virgules."""
    if millesimes is None:
        return None
    try:
        return sorted({date.fromisoformat(value) for value in split_codes(millesimes)})
    except ValueError as error:
        raise ValueError(
            f"Millésimes invalides : {millesimes} (format attendu AAAA-MM-JJ)."
        ) from error


def parse_departements(departements: str | None) -> list[str] | None:
    """Normalise et valide les codes départementaux demandés."""
    if departements is None:
        return None
    codes = list(
        dict.fromkeys(
            normalize_department_code(code) for code in split_codes(departements)
        )
    )
    invalid = [code for code in codes if not DEPARTEMENT_PATTERN.fullmatch(code)]
    if not codes or invalid:
        raise ValueError(f"Codes de département invalides : {departements}")
    return codes


def is_eligible_millesime(millesime: date) -> bool:
    """Indique si le millésime entre dans le périmètre de l'historique."""
    return millesime >= FIRST_MILLESIME and millesime not in EXCLUDED_MILLESIMES


def select_millesimes(
    available: list[date], requested: list[date] | None
) -> list[date]:
    """Sélectionne les millésimes à traiter, par ordre chronologique."""
    if requested is None:
        return [
            millesime for millesime in available if is_eligible_millesime(millesime)
        ]
    unknown = [millesime for millesime in requested if millesime not in available]
    if unknown:
        raise ValueError(
            "Millésimes non publiés : "
            + ", ".join(millesime.isoformat() for millesime in unknown)
        )
    ineligible = [
        millesime for millesime in requested if not is_eligible_millesime(millesime)
    ]
    if ineligible:
        raise ValueError(
            "Millésimes hors périmètre (antérieurs au "
            f"{FIRST_MILLESIME.isoformat()} ou publiés uniquement à la commune) : "
            + ", ".join(millesime.isoformat() for millesime in ineligible)
        )
    return sorted(requested)


def source_format(millesime: date) -> str:
    """Renvoie le format utilisé pour un millésime : GeoParquet ou shapefile."""
    return "geoparquet" if millesime >= FIRST_GEOPARQUET_MILLESIME else "shp"


def build_source_location(base_location: str, millesime: date, departement: str) -> str:
    """Construit l'URL ou le chemin de la source d'un département et millésime."""
    base = base_location.rstrip("/")
    if source_format(millesime) == "geoparquet":
        return f"{base}/{millesime.isoformat()}/geoparquet/france/cadastre.parquet"
    return (
        f"{base}/{millesime.isoformat()}/shp/departements/{departement}/"
        f"cadastre-{departement}-parcelles-shp.zip"
    )


@contextmanager
def open_geoparquet_source(location: str, departement: str) -> Iterator[ParcelSource]:
    """Ouvre les parcelles d'un département dans le GeoParquet national."""
    connection = duckdb.connect()
    try:
        if is_remote(location):
            connection.execute("INSTALL httpfs; LOAD httpfs")
        # Le CRS global est erroné : conserver le WKB et utiliser geom_srid par objet.
        connection.execute("SET enable_geoparquet_conversion = false")
        source_filter = "type_objet = 'parcelles' AND departement = ?"

        def read_ids() -> list[str]:
            """Lit uniquement la colonne des identifiants."""
            rows = connection.execute(
                f"SELECT id FROM read_parquet(?) WHERE {source_filter}",
                [location, departement],
            ).fetchall()
            return [row[0] for row in rows]

        def iter_rows(selected_ids: set[str]) -> Iterator[ParcelRow]:
            """Lit les attributs et géométries des identifiants sélectionnés."""
            connection.register(
                "selected_ids", pd.DataFrame({"id": sorted(selected_ids)}, dtype=object)
            )
            columns = ", ".join(f'"{column}"' for column, _ in PARCEL_COLUMNS)
            connection.execute(
                f"""
                SELECT {columns}, geometry, geom_srid
                FROM read_parquet(?)
                WHERE {source_filter} AND id IN (SELECT id FROM selected_ids)
                """,
                [location, departement],
            )
            while rows := connection.fetchmany(BATCH_SIZE):
                yield from rows
            connection.unregister("selected_ids")

        yield ParcelSource(read_ids, iter_rows)
    finally:
        connection.close()


def shapefile_srid(shapefile: Path) -> int:
    """Détermine le code EPSG de la projection déclarée par le shapefile."""
    crs = pyogrio.read_info(shapefile)["crs"]
    srid = CRS.from_user_input(crs).to_epsg() if crs else None
    if srid is None:
        raise ValueError(f"Projection non reconnue pour {shapefile} : {crs}")
    return srid


def to_python_value(value, column_type: str):
    """Convertit une valeur lue par pyogrio en valeur Python insérable."""
    if column_type == "date" and isinstance(value, str):
        return date.fromisoformat(value[:10].replace("/", "-")) if value else None
    if isinstance(value, np.datetime64):
        return None if np.isnat(value) else value.astype("datetime64[D]").item()
    if isinstance(value, np.floating):
        return None if np.isnan(value) else int(round(float(value)))
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, str):
        return value or None
    return value


def read_shapefile(shapefile: Path, **kwargs) -> tuple:
    """Lit un shapefile avec pyogrio en masquant les avertissements de format.

    Certains millésimes anciens contiennent des contenances mal formées (« . »),
    lues comme nulles ou nulles en valeur : ces avertissements sont non bloquants.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return pyogrio.raw.read(shapefile, **kwargs)


@contextmanager
def open_shapefile_source(location: str) -> Iterator[ParcelSource]:
    """Ouvre l'archive shapefile départementale des parcelles."""
    temp_root = Path(TEMP_DIR)
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as temp_dir:
        archive = Path(location)
        if is_remote(location):
            archive = download_file(location, Path(temp_dir) / Path(location).name)
        with zipfile.ZipFile(archive) as zip_file:
            zip_file.extractall(temp_dir)
        shapefiles = sorted(Path(temp_dir).rglob("*.shp"))
        if len(shapefiles) != 1:
            raise ValueError(
                f"Un seul shapefile attendu dans {location}, trouvé : {len(shapefiles)}"
            )
        shapefile = shapefiles[0]
        srid = shapefile_srid(shapefile)
        column_names = [column for column, _ in PARCEL_COLUMNS]
        index: dict[str, np.ndarray] = {}

        def read_ids() -> list[str]:
            """Lit les identifiants et mémorise leur FID pour la seconde lecture."""
            _, fids, _, fields = read_shapefile(
                shapefile, columns=["id"], read_geometry=False, return_fids=True
            )
            index["ids"] = fields[0].astype(object)
            index["fids"] = fids
            return [value for value in index["ids"].tolist() if value]

        def iter_rows(selected_ids: set[str]) -> Iterator[ParcelRow]:
            """Lit les seules entités sélectionnées, par lots de FID."""
            if "ids" not in index:
                read_ids()
            mask = np.fromiter(
                (value in selected_ids for value in index["ids"]),
                dtype=bool,
                count=len(index["ids"]),
            )
            selected_fids = index["fids"][mask]
            for start in range(0, len(selected_fids), BATCH_SIZE):
                meta, _, geometries, fields = read_shapefile(
                    shapefile,
                    columns=column_names,
                    fids=selected_fids[start : start + BATCH_SIZE],
                )
                positions = {
                    name: position for position, name in enumerate(meta["fields"])
                }
                ordered = [fields[positions[name]] for name in column_names]
                for row_index, geometry in enumerate(geometries):
                    values = [
                        to_python_value(column[row_index], column_type)
                        for column, (_, column_type) in zip(
                            ordered, PARCEL_COLUMNS, strict=True
                        )
                    ]
                    yield (*values, geometry, srid)

        yield ParcelSource(read_ids, iter_rows)


@contextmanager
def open_parcel_source(
    base_location: str, millesime: date, departement: str
) -> Iterator[ParcelSource]:
    """Ouvre la source adaptée au format du millésime."""
    location = build_source_location(base_location, millesime, departement)
    if source_format(millesime) == "geoparquet":
        if not is_remote(location):
            location = str(Path(location).expanduser().resolve(strict=True))
        with open_geoparquet_source(location, departement) as source:
            yield source
    else:
        with open_shapefile_source(location) as source:
            yield source


def ensure_history_tables(connection, schema: str) -> None:
    """Crée les tables, index, vue et fonction de l'historique s'ils sont absents."""
    quote = connection.dialect.identifier_preparer.quote
    history = f"{quote(schema)}.{quote(HISTORY_TABLE)}"
    import_log = f"{quote(schema)}.{quote(IMPORT_LOG_TABLE)}"
    attributes = ", ".join(
        f"{quote(column)} {column_type}" + (" NOT NULL" if column == "id" else "")
        for column, column_type in PARCEL_COLUMNS
    )
    statements = [
        f"CREATE SCHEMA IF NOT EXISTS {quote(schema)}",
        f"""
        CREATE TABLE IF NOT EXISTS {history} (
            fid bigserial PRIMARY KEY,
            departement text NOT NULL,
            {attributes},
            geom_srid integer NOT NULL,
            millesime_debut date NOT NULL,
            millesime_fin date,
            periode daterange GENERATED ALWAYS AS
                (daterange(millesime_debut, millesime_fin, '[)')) STORED,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            CONSTRAINT {quote(HISTORY_TABLE + "_periode_check")}
                CHECK (millesime_fin IS NULL OR millesime_fin > millesime_debut),
            CONSTRAINT {quote(HISTORY_TABLE + "_id_debut_key")}
                UNIQUE (id, millesime_debut)
        )
        """,
        # Une seule version active par identifiant.
        f"CREATE UNIQUE INDEX IF NOT EXISTS {quote(HISTORY_TABLE + '_actif_id_idx')} "
        f"ON {history} (id) WHERE millesime_fin IS NULL",
        f"CREATE INDEX IF NOT EXISTS {quote(HISTORY_TABLE + '_actif_dep_idx')} "
        f"ON {history} (departement) WHERE millesime_fin IS NULL",
        f"CREATE INDEX IF NOT EXISTS {quote(HISTORY_TABLE + '_periode_idx')} "
        f"ON {history} USING gist (periode)",
        f"CREATE INDEX IF NOT EXISTS {quote(HISTORY_TABLE + '_geom_idx')} "
        f"ON {history} USING gist (geom)",
        f"CREATE INDEX IF NOT EXISTS {quote(HISTORY_TABLE + '_commune_idx')} "
        f"ON {history} (commune)",
        f"""
        CREATE TABLE IF NOT EXISTS {import_log} (
            departement text NOT NULL,
            millesime date NOT NULL,
            format text NOT NULL,
            source text NOT NULL,
            nb_parcelles integer NOT NULL,
            nb_nouvelles integer NOT NULL,
            nb_disparues integer NOT NULL,
            imported_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (departement, millesime)
        )
        """,
        f"""
        CREATE OR REPLACE VIEW {quote(schema)}.{quote(CURRENT_VIEW)} AS
        SELECT * FROM {history} WHERE millesime_fin IS NULL
        """,
        f"""
        CREATE OR REPLACE FUNCTION {quote(schema)}.{quote(MILLESIME_FUNCTION)}(
            p_millesime date
        )
        RETURNS SETOF {history}
        LANGUAGE sql STABLE
        AS $$ SELECT * FROM {history} WHERE periode @> p_millesime $$
        """,
        f"COMMENT ON TABLE {history} IS "
        "'Historique des parcelles Etalab : une ligne par période d''existence. "
        "millesime_fin est le premier millésime où la parcelle n''existe plus.'",
        f"COMMENT ON TABLE {import_log} IS "
        "'Journal des millésimes importés par département dans l''historique.'",
    ]
    for statement in statements:
        connection.execute(text(statement))


def read_last_imported_millesimes(connection, schema: str) -> dict[str, date]:
    """Renvoie le dernier millésime importé pour chaque département."""
    quote = connection.dialect.identifier_preparer.quote
    rows = connection.execute(
        text(
            "SELECT departement, max(millesime) "
            f"FROM {quote(schema)}.{quote(IMPORT_LOG_TABLE)} GROUP BY departement"
        )
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def escape_copy_value(value: str) -> str:
    """Échappe une valeur pour le format texte de COPY."""
    return (
        value.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def apply_millesime(
    connection,
    schema: str,
    departement: str,
    millesime: date,
    source: ParcelSource,
    source_ids: set[str],
) -> tuple[int, int, int]:
    """Clôt les parcelles disparues puis insère les nouvelles parcelles.

    Returns:
        tuple: (parcelles disparues, parcelles insérées, nouvelles non insérées).
    """
    quote = connection.dialect.identifier_preparer.quote
    history = f"{quote(schema)}.{quote(HISTORY_TABLE)}"
    columns = ", ".join(
        ["departement", *(quote(column) for column, _ in PARCEL_COLUMNS)]
        + ["geom_srid", "millesime_debut", "geom"]
    )
    template = (
        "(%s, "
        + ", ".join(["%s"] * len(PARCEL_COLUMNS))
        + ", %s, %s, ST_Multi(ST_Force2D(ST_Transform("
        "ST_SetSRID(ST_GeomFromWKB(%s), %s), 2154))))"
    )
    with connection.connection.cursor() as cursor:
        cursor.execute(
            "CREATE TEMP TABLE source_ids (id text PRIMARY KEY) ON COMMIT DROP"
        )
        cursor.copy_expert(
            "COPY source_ids (id) FROM STDIN",
            StringIO("".join(f"{escape_copy_value(value)}\n" for value in source_ids)),
        )
        cursor.execute("ANALYZE source_ids")
        cursor.execute(
            f"""
            UPDATE {history} AS parcelle SET millesime_fin = %s
            WHERE parcelle.departement = %s
              AND parcelle.millesime_fin IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM source_ids WHERE source_ids.id = parcelle.id
              )
            """,
            (millesime, departement),
        )
        closed_count = cursor.rowcount
        cursor.execute(
            f"""
            SELECT source_ids.id FROM source_ids
            WHERE NOT EXISTS (
                SELECT 1 FROM {history} AS parcelle
                WHERE parcelle.id = source_ids.id AND parcelle.millesime_fin IS NULL
            )
            """
        )
        new_ids = {row[0] for row in cursor.fetchall()}
        inserted_ids: set[str] = set()
        batch: list[tuple] = []

        def flush() -> None:
            """Insère le lot courant de nouvelles parcelles."""
            execute_values(
                cursor,
                f"INSERT INTO {history} ({columns}) VALUES %s",
                batch,
                template=template,
                page_size=BATCH_SIZE,
            )
            batch.clear()

        if new_ids:
            for *values, geometry, srid in source.iter_rows(new_ids):
                parcel_id = values[0]
                if parcel_id in inserted_ids or parcel_id not in new_ids:
                    continue
                if geometry is None or not srid:
                    continue
                inserted_ids.add(parcel_id)
                batch.append((departement, *values, srid, millesime, geometry, srid))
                if len(batch) >= BATCH_SIZE:
                    flush()
            if batch:
                flush()
    return closed_count, len(inserted_ids), len(new_ids) - len(inserted_ids)


def is_not_found_error(error: Exception) -> bool:
    """Indique si l'erreur HTTP (requests ou DuckDB) correspond à un 404."""
    if isinstance(error, requests.HTTPError):
        return error.response is not None and error.response.status_code == 404
    return getattr(error, "status_code", None) == 404


@contextmanager
def hold_flow_lock(engine, schema: str) -> Iterator[None]:
    """Empêche deux constructions concurrentes de l'historique dans un schéma.

    Le verrou de session est conservé pendant tout le flow afin que les
    millésimes d'un département soient intégrés dans l'ordre chronologique.
    """
    lock_name = f"{schema}.{HISTORY_TABLE}.flow"
    with engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_name))"),
            {"lock_name": lock_name},
        )
        connection.commit()
        if not acquired:
            raise RuntimeError(
                f"Un autre import de l'historique des parcelles est en cours "
                f"dans le schéma {schema}."
            )
        try:
            yield
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(hashtext(:lock_name))"),
                {"lock_name": lock_name},
            )
            connection.commit()


def import_departement_millesime(
    engine,
    schema: str,
    base_location: str,
    departement: str,
    millesime: date,
    open_source: Callable = open_parcel_source,
) -> dict | None:
    """Intègre un millésime d'un département dans l'historique, en une transaction.

    Returns:
        dict | None: les compteurs de l'import, ou None si l'import est ignoré.
    """
    location = build_source_location(base_location, millesime, departement)
    try:
        with open_source(base_location, millesime, departement) as source:
            ids = source.read_ids()
            source_ids = set(ids)
            if not source_ids:
                logger.warning(
                    "Aucune parcelle pour le département %s au millésime %s : "
                    "import ignoré.",
                    departement,
                    millesime,
                )
                return None
            if len(source_ids) != len(ids):
                logger.warning(
                    "%d identifiants de parcelle en double ou vides ignorés "
                    "(département %s, millésime %s).",
                    len(ids) - len(source_ids),
                    departement,
                    millesime,
                )
            with engine.begin() as connection:
                quote = connection.dialect.identifier_preparer.quote
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
                    {"lock_name": f"{schema}.{HISTORY_TABLE}.{departement}"},
                )
                last_millesime = read_last_imported_millesimes(connection, schema).get(
                    departement
                )
                if last_millesime is not None and millesime <= last_millesime:
                    logger.warning(
                        "Département %s : millésime %s non postérieur au dernier "
                        "millésime importé (%s), import ignoré.",
                        departement,
                        millesime,
                        last_millesime,
                    )
                    return None
                active_count = connection.scalar(
                    text(
                        f"SELECT count(*) FROM {quote(schema)}.{quote(HISTORY_TABLE)} "
                        "WHERE departement = :departement AND millesime_fin IS NULL"
                    ),
                    {"departement": departement},
                )
                closed_count, new_count, not_inserted_count = apply_millesime(
                    connection, schema, departement, millesime, source, source_ids
                )
                connection.execute(
                    text(
                        f"INSERT INTO {quote(schema)}.{quote(IMPORT_LOG_TABLE)} "
                        "(departement, millesime, format, source, nb_parcelles, "
                        "nb_nouvelles, nb_disparues) VALUES (:departement, "
                        ":millesime, :format, :source, :nb_parcelles, "
                        ":nb_nouvelles, :nb_disparues)"
                    ),
                    {
                        "departement": departement,
                        "millesime": millesime,
                        "format": source_format(millesime),
                        "source": location,
                        "nb_parcelles": len(source_ids),
                        "nb_nouvelles": new_count,
                        "nb_disparues": closed_count,
                    },
                )
    except (requests.HTTPError, duckdb.HTTPException) as error:
        if is_not_found_error(error):
            logger.warning(
                "Source absente pour le département %s au millésime %s (%s) : "
                "import ignoré.",
                departement,
                millesime,
                location,
            )
            return None
        raise
    if not_inserted_count:
        # Ces parcelles restent absentes des parcelles actives : elles seront
        # insérées au prochain millésime qui fournit leur géométrie.
        logger.warning(
            "Département %s, millésime %s : %d parcelles nouvelles sans géométrie "
            "ou SRID non insérées.",
            departement,
            millesime,
            not_inserted_count,
        )
    if active_count and closed_count > CLOSED_RATIO_WARNING * active_count:
        logger.warning(
            "Département %s, millésime %s : %d parcelles disparues sur %d actives, "
            "vérifier la complétude de la source.",
            departement,
            millesime,
            closed_count,
            active_count,
        )
    logger.info(
        "Département %s, millésime %s (%s) : %d parcelles, %d nouvelles, %d disparues.",
        departement,
        millesime,
        source_format(millesime),
        len(source_ids),
        new_count,
        closed_count,
    )
    return {
        "departement": departement,
        "millesime": millesime,
        "format": source_format(millesime),
        "nb_parcelles": len(source_ids),
        "nb_nouvelles": new_count,
        "nb_disparues": closed_count,
    }


@flow
def import_parcelles_historique_flow(
    departements: str | None = None,
    millesimes: str | None = None,
    db_schema: str = "public",
    base_location: str = ETALAB_CADASTRE_URL,
) -> list[dict]:
    """Construit ou complète l'historique des parcelles, millésime par millésime.

    Seuls les millésimes postérieurs au dernier millésime importé pour chaque
    département sont traités : les parcelles nouvelles sont insérées et les
    parcelles absentes sont clôturées.

    Args:
        departements: codes départementaux séparés par des virgules ; par défaut
            tous les départements publiés pour chaque millésime.
        millesimes: dates ISO séparées par des virgules ; par défaut tous les
            millésimes publiés depuis le 3 avril 2018.
        db_schema: schéma PostgreSQL de destination.
        base_location: URL ou répertoire local reproduisant l'arborescence Etalab.

    Returns:
        list[dict]: les compteurs de chaque import département × millésime.
    """
    requested_departements = parse_departements(departements)
    selected_millesimes = select_millesimes(
        list_available_millesimes(base_location), parse_millesimes(millesimes)
    )
    logger.info(
        "Historique des parcelles : %d millésimes candidats (%s à %s).",
        len(selected_millesimes),
        selected_millesimes[0] if selected_millesimes else "-",
        selected_millesimes[-1] if selected_millesimes else "-",
    )
    results: list[dict] = []
    engine = create_engine()
    try:
        with hold_flow_lock(engine, db_schema):
            with engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
                    {"lock_name": f"{db_schema}.{HISTORY_TABLE}"},
                )
                ensure_history_tables(connection, db_schema)
                last_imported = read_last_imported_millesimes(connection, db_schema)
            for millesime in selected_millesimes:
                millesime_departements = requested_departements or list_departements(
                    base_location, millesime
                )
                for departement in millesime_departements:
                    last_millesime = last_imported.get(departement)
                    if last_millesime is not None and millesime <= last_millesime:
                        if millesime < last_millesime:
                            logger.warning(
                                "Département %s : millésime %s antérieur au dernier "
                                "millésime importé (%s), ignoré. Reconstruire la table "
                                "pour intégrer un millésime antérieur.",
                                departement,
                                millesime,
                                last_millesime,
                            )
                        continue
                    result = import_departement_millesime(
                        engine, db_schema, base_location, departement, millesime
                    )
                    if result is not None:
                        last_imported[departement] = millesime
                        results.append(result)
    finally:
        engine.dispose()
    logger.info(
        "Historique des parcelles : %d imports réalisés, %d parcelles nouvelles, "
        "%d disparues.",
        len(results),
        sum(result["nb_nouvelles"] for result in results),
        sum(result["nb_disparues"] for result in results),
    )
    return results
