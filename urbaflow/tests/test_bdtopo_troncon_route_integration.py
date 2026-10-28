"""Validation GDAL/PostGIS, activée par BDTOPO_TEST_DATABASE_URL."""

import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import geopandas as gpd
import pytest
from flows.bdtopo import import_bdtopo_troncon_route as route_import
from shapely.geometry import LineString
from shared_tasks.geopf_utils import GeopfResource
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def postgis_database(monkeypatch):
    """Crée un schéma isolé dans une base de test explicitement configurée."""
    database_url = os.environ.get("BDTOPO_TEST_DATABASE_URL")
    if not database_url or not shutil.which("ogr2ogr"):
        pytest.skip("BDTOPO_TEST_DATABASE_URL et ogr2ogr sont requis.")
    engine = create_engine(database_url)
    schema = f"test_bdtopo_route_{uuid4().hex[:12]}"
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    monkeypatch.setattr(route_import, "create_engine", lambda: engine)
    for key, value in {
        "POSTGRES_HOST": engine.url.host,
        "POSTGRES_PORT": str(engine.url.port or 5432),
        "POSTGRES_DB": engine.url.database,
        "POSTGRES_USER": engine.url.username,
        "POSTGRES_PASS": engine.url.password or "",
    }.items():
        monkeypatch.setenv(key, value)
    try:
        yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        engine.dispose()


def write_geopackage(path: Path, rows: list[dict]) -> Path:
    """Écrit une livraison miniature avec des lignes 3D en Lambert-93."""
    geometry = LineString([(350000, 6780000, 10), (350100, 6780100, 20)])
    dataframe = gpd.GeoDataFrame(rows, geometry=[geometry] * len(rows), crs="EPSG:2154")
    dataframe.to_file(path, layer=route_import.ROUTE_LAYER, driver="GPKG")
    return path


def test_real_import_reimport_and_rollback(
    monkeypatch, tmp_path, postgis_database
) -> None:
    """Valide le périmètre, les géométries, l'idempotence et le rollback réels."""
    engine, schema = postgis_database
    resource = GeopfResource("BDTOPO_TEST", "2026-06-15", "https://example.org/test.7z")
    rows = [
        {
            "cleabs": "route-interieure",
            "nature": "Route à 1 chaussée",
            "insee_commune_gauche": "35001",
            "insee_commune_droite": "35002",
        },
        {
            "cleabs": "route-limitrophe",
            "nature": "Route à 2 chaussées",
            "insee_commune_gauche": "22001",
            "insee_commune_droite": "35003",
        },
        {
            "cleabs": "route-exterieure",
            "nature": "Chemin",
            "insee_commune_gauche": "22002",
            "insee_commune_droite": None,
        },
    ]
    geopackage = write_geopackage(tmp_path / "source.gpkg", rows)
    download = MagicMock(return_value=geopackage)
    monkeypatch.setattr(route_import, "DOWNLOAD_DIR", tmp_path / "downloads")
    monkeypatch.setattr(
        route_import, "find_geopf_resource", MagicMock(return_value=resource)
    )
    monkeypatch.setattr(route_import, "download_route_geopackage", download)
    for task_name in (
        "load_route_staging",
        "replace_department_routes",
        "drop_route_staging",
    ):
        monkeypatch.setattr(
            route_import, task_name, getattr(route_import, task_name).fn
        )

    def run_import(department: str) -> None:
        """Exécute le flux avec les vrais chargements GDAL et transactions SQL."""
        route_import.import_bdtopo_troncon_route_flow.fn(department, db_schema=schema)

    def read_routes() -> list[tuple]:
        """Lit le contenu attributaire et les caractéristiques géométriques."""
        with engine.connect() as connection:
            return [
                tuple(row)
                for row in connection.execute(
                    text(
                        f"""
                        SELECT code_departement, cleabs, nature, millesime::text,
                            ST_GeometryType(geom), ST_NDims(geom), ST_SRID(geom)
                        FROM {schema}.bdtopo_troncon_de_route
                        ORDER BY code_departement, cleabs
                        """
                    )
                )
            ]

    run_import("35")
    initial = read_routes()
    assert len(initial) == 2
    assert {row[1] for row in initial} == {"route-interieure", "route-limitrophe"}
    assert all(
        row[3:] == ("2026-06-15", "ST_MultiLineString", 2, 2154) for row in initial
    )
    run_import("35")
    assert read_routes() == initial

    run_import("22")
    assert len(read_routes()) == 4
    other_department = [row for row in read_routes() if row[0] == "22"]
    updated = [{**rows[0], "nature": "Route modifiée"}]
    download.return_value = write_geopackage(tmp_path / "updated.gpkg", updated)
    run_import("35")
    successful_import = read_routes()
    assert len(successful_import) == 3
    assert [row for row in successful_import if row[0] == "22"] == other_department
    assert [row[2] for row in successful_import if row[0] == "35"] == ["Route modifiée"]

    download.return_value = write_geopackage(
        tmp_path / "duplicate.gpkg", [rows[0], rows[0]]
    )
    with pytest.raises(IntegrityError):
        run_import("35")
    assert read_routes() == successful_import

    download.return_value = write_geopackage(tmp_path / "outside.gpkg", [rows[2]])
    with pytest.raises(ValueError, match="Aucun tronçon"):
        run_import("35")
    assert read_routes() == successful_import
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    """
                SELECT count(*) FROM information_schema.tables
                WHERE table_schema = :schema
                    AND table_name LIKE 'bdtopo_route_staging_%'
                """
                ),
                {"schema": schema},
            ).scalar_one()
            == 0
        )
    assert not list((tmp_path / "downloads").iterdir())
