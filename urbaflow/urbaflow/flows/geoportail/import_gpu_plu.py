import json
import re
import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import create_table_from_geodataframe, load
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

logger = get_logger(__name__)

APICARTO_GPU_URL = "https://apicarto.ign.fr/api/gpu"
GEO_API_COMMUNES_URL = "https://geo.api.gouv.fr/communes"
DEFAULT_DOWNLOAD_DIR = Path(TEMP_DIR) / "geoportail/plu"

GPU_PLU_LAYERS = (
    "zone_urba",
    "prescription_surf",
    "prescription_lin",
    "prescription_pct",
    "info_surf",
)


def validate_perimeter_code(code: str, expected_length: int, label: str) -> str:
    """Valide et normalise un code de périmètre."""
    normalized_code = str(code).strip()
    if not re.fullmatch(rf"\d{{{expected_length}}}", normalized_code):
        raise ValueError(
            f"Le {label} doit contenir exactement {expected_length} chiffres."
        )
    return normalized_code


@task
def resolve_gpu_partitions(
    epci: str | None = None,
    commune: str | None = None,
) -> tuple[str, list[str]]:
    """Résout les partitions GPU correspondant à un EPCI ou une commune."""
    if bool(epci) == bool(commune):
        raise ValueError("Renseigner exactement un périmètre : --epci ou --commune.")

    if commune:
        commune_code = validate_perimeter_code(commune, 5, "code commune")
        return commune_code, [f"DU_{commune_code}", f"PSMV_{commune_code}"]

    epci_code = validate_perimeter_code(epci or "", 9, "code EPCI")
    response = requests.get(
        GEO_API_COMMUNES_URL,
        params={"codeEpci": epci_code, "fields": "code,nom"},
        timeout=30,
    )
    response.raise_for_status()
    communes = response.json()
    if not communes:
        raise ValueError(
            f"Aucune commune trouvée pour l'EPCI {epci_code}. "
            "Vérifier le code fourni."
        )

    commune_codes = sorted(
        validate_perimeter_code(commune_data["code"], 5, "code commune")
        for commune_data in communes
    )
    partition_codes = [epci_code, *commune_codes]
    partitions = [
        f"{prefix}_{partition_code}"
        for partition_code in partition_codes
        for prefix in ("DU", "PSMV")
    ]
    logger.info(
        "EPCI %s : %d commune(s) et %d partition(s) GPU à interroger",
        epci_code,
        len(commune_codes),
        len(partitions),
    )
    return epci_code, partitions


def download_partition(
    layer_name: str,
    partition: str,
    destination_path: Path,
) -> list[dict]:
    """Télécharge une partition GPU au format GeoJSON."""
    endpoint = layer_name.replace("_", "-")
    response = requests.get(
        f"{APICARTO_GPU_URL}/{endpoint}",
        params={"partition": partition},
        timeout=120,
    )
    response.raise_for_status()
    feature_collection = response.json()
    if feature_collection.get("type") != "FeatureCollection":
        raise ValueError(
            f"Réponse APICARTO invalide pour la couche {layer_name}, "
            f"partition {partition}."
        )

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination_path.with_suffix(".geojson.tmp")
    with temporary_path.open("w", encoding="utf-8") as destination_file:
        json.dump(feature_collection, destination_file, ensure_ascii=False)
    temporary_path.replace(destination_path)

    features = feature_collection.get("features", [])
    logger.info(
        "Couche %s, partition %s : %d objet(s) téléchargé(s) dans %s",
        layer_name,
        partition,
        len(features),
        destination_path,
    )
    return features


@task
def download_gpu_plu_data(
    perimeter_code: str,
    partitions: list[str],
    download_dir: Path = DEFAULT_DOWNLOAD_DIR,
) -> dict[str, list[dict]]:
    """Télécharge les cinq couches PLU pour toutes les partitions du périmètre."""
    perimeter_dir = download_dir / perimeter_code
    features_by_layer = {}

    for layer_name in GPU_PLU_LAYERS:
        layer_features = []
        for partition in partitions:
            destination_path = perimeter_dir / layer_name / f"{partition}.geojson"
            layer_features.extend(
                download_partition(layer_name, partition, destination_path)
            )
        features_by_layer[layer_name] = layer_features

    return features_by_layer


def prepare_layer_geodataframe(features: list[dict]) -> gpd.GeoDataFrame:
    """Prépare les objets GPU pour leur chargement dans PostGIS."""
    geodataframe = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    geodataframe = geodataframe.to_crs("EPSG:2154").rename_geometry("geom")

    if "gid" in geodataframe.columns:
        geodataframe["gid"] = geodataframe["gid"].astype(str)
        geodataframe = geodataframe.drop_duplicates(subset=["gid"])

    return geodataframe


def postgres_column_type(series: pd.Series) -> str:
    """Détermine un type PostgreSQL adapté à une série pandas."""
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "bigint"
    if pd.api.types.is_float_dtype(series):
        return "double precision"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "timestamp"
    return "text"


@task
def import_gpu_plu_layer(
    layer_name: str,
    features: list[dict],
    partitions: list[str],
    schema: str = "public",
) -> None:
    """Remplace les partitions téléchargées dans une table PLU PostGIS."""
    table_name = f"urba_{layer_name}"
    engine = create_engine()

    if features:
        geodataframe = prepare_layer_geodataframe(features)
    else:
        geodataframe = None

    with engine.begin() as connection:
        quote = connection.engine.dialect.identifier_preparer.quote
        qualified_table = f"{quote(schema)}.{quote(table_name)}"
        table_exists = connection.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_name = :table)"
            ),
            {"schema": schema, "table": table_name},
        ).scalar_one()

        if not table_exists:
            if geodataframe is None:
                connection.execute(
                    DDL(
                        f"CREATE TABLE {qualified_table} ("
                        f"{quote('gid')} text, "
                        f"{quote('partition')} text, "
                        f"{quote('geom')} geometry(GEOMETRY, 2154))"
                    )
                )
            else:
                create_table_from_geodataframe(
                    gdf=geodataframe,
                    connection=connection,
                    table_name=table_name,
                    schema=schema,
                    logger=logger,
                    srs=2154,
                )
            connection.execute(
                DDL(
                    f"CREATE INDEX {quote(f'sidx_{table_name}_geom')} "
                    f"ON {qualified_table} USING GIST ({quote('geom')})"
                )
            )

        connection.execute(
            text(
                f"DELETE FROM {qualified_table} "
                f"WHERE {quote('partition')} = ANY(:partitions)"
            ),
            {"partitions": partitions},
        )

        if geodataframe is None:
            logger.info(
                "Aucune donnée à insérer dans %s.%s pour le périmètre demandé",
                schema,
                table_name,
            )
            return

        existing_columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": schema, "table": table_name},
            )
            .scalars()
            .all()
        )
        for column_name in geodataframe.columns:
            if column_name == "geom" or column_name in existing_columns:
                continue
            column_type = postgres_column_type(geodataframe[column_name])
            connection.execute(
                DDL(
                    f"ALTER TABLE {qualified_table} "
                    f"ADD COLUMN {quote(column_name)} {column_type}"
                )
            )

        load(
            geodataframe,
            connection=connection,
            table_name=table_name,
            schema=schema,
            how="append",
            logger=logger,
        )
        logger.info(
            "%d objet(s) importé(s) dans %s.%s",
            len(geodataframe),
            schema,
            table_name,
        )


@flow(name="import-gpu-plu")
def import_gpu_plu_flow(
    epci: str | None = None,
    commune: str | None = None,
    db_schema: str = "public",
    download_dir: Path = DEFAULT_DOWNLOAD_DIR,
    keep_files: bool = True,
) -> None:
    """Télécharge et importe les données PLU d'un EPCI ou d'une commune."""
    perimeter_code, partitions = resolve_gpu_partitions(
        epci=epci,
        commune=commune,
    )
    features_by_layer = download_gpu_plu_data(
        perimeter_code=perimeter_code,
        partitions=partitions,
        download_dir=download_dir,
    )

    for layer_name in GPU_PLU_LAYERS:
        import_gpu_plu_layer(
            layer_name=layer_name,
            features=features_by_layer[layer_name],
            partitions=partitions,
            schema=db_schema,
        )

    if not keep_files:
        perimeter_dir = download_dir / perimeter_code
        shutil.rmtree(perimeter_dir)
        logger.info("Fichiers téléchargés supprimés dans %s", perimeter_dir)

    logger.info(
        "Import PLU terminé pour le périmètre %s dans les tables urba_*",
        perimeter_code,
    )
