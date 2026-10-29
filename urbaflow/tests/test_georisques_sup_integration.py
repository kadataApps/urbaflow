"""Validation PostGIS activée par SUP_TEST_DATABASE_URL."""

import json
import os
from uuid import uuid4

import pytest
from flows.georisques import import_sup
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DataError


@pytest.fixture
def postgis_database(monkeypatch):
    """Crée un schéma isolé dans une base de test explicitement configurée."""
    database_url = os.environ.get("SUP_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("SUP_TEST_DATABASE_URL est requis.")
    engine = create_engine(database_url)
    schema = f"test_sup_{uuid4().hex[:12]}"
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    monkeypatch.setattr(import_sup, "create_engine", lambda: engine)
    try:
        yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        engine.dispose()


@pytest.mark.parametrize("existing_column", [False, True])
def test_geometry_type_population_and_repeated_conversion(
    postgis_database, existing_column
) -> None:
    """Vérifie le type déclaré, la migration sans perte et la reprojection."""
    engine, schema = postgis_database
    import_sup.create_table_sup.fn(schema=schema, recreate=False)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"INSERT INTO {schema}.risques_sup (identifiant_ssp) "
                "VALUES ('polygon'), ('multipolygon'), ('null')"
            )
        )
        if existing_column:
            connection.execute(
                text(
                    f"ALTER TABLE {schema}.risques_sup "
                    "ADD COLUMN geom geometry(GEOMETRY, 2154)"
                )
            )
            connection.execute(
                text(
                    f"UPDATE {schema}.risques_sup SET geom = ST_GeomFromText("
                    "'POLYGON((700000 6600000, 700100 6600000, "
                    "700100 6600100, 700000 6600000))', 2154) "
                    "WHERE identifiant_ssp != 'null'"
                )
            )
            connection.execute(
                text(
                    f"UPDATE {schema}.risques_sup SET geom = ST_Multi(geom) "
                    "WHERE identifiant_ssp = 'multipolygon'"
                )
            )

    for _ in range(2):
        import_sup.add_geometry_column_to_table.fn(schema=schema)
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT type, srid FROM geometry_columns "
                    "WHERE f_table_schema = :schema AND f_table_name = 'risques_sup'"
                ),
                {"schema": schema},
            ).one() == ("MULTIPOLYGON", 2154)
            rows = connection.execute(
                text(
                    f"SELECT identifiant_ssp, ST_GeometryType(geom), ST_SRID(geom) "
                    f"FROM {schema}.risques_sup ORDER BY identifiant_ssp"
                )
            ).all()
            assert len(rows) == 3
            assert rows[1] == ("null", None, None)
            for row in (rows[0], rows[2]):
                assert row[1:] == (
                    ("ST_MultiPolygon", 2154) if existing_column else (None, None)
                )

    polygon = {
        "type": "Polygon",
        "coordinates": [[[0, 6000000], [100, 6000000], [100, 6000100], [0, 6000000]]],
    }
    multipolygon = {
        "type": "MultiPolygon",
        "coordinates": [polygon["coordinates"]],
    }
    with engine.begin() as connection:
        for identifier, geometry in (
            ("polygon", polygon),
            ("multipolygon", multipolygon),
        ):
            connection.execute(
                text(
                    f"UPDATE {schema}.risques_sup SET bbox_geojson = :geometry "
                    "WHERE identifiant_ssp = :identifier"
                ),
                {"geometry": json.dumps(geometry), "identifier": identifier},
            )
    import_sup.populate_geom.fn(schema=schema)
    with engine.connect() as connection:
        assert connection.execute(
            text(
                f"SELECT ST_GeometryType(geom), ST_SRID(geom), "
                "ST_Equals(geom, ST_Multi(ST_Transform(ST_SetSRID("
                "ST_GeomFromGeoJSON(bbox_geojson), 3857), 2154))) "
                f"FROM {schema}.risques_sup WHERE bbox_geojson IS NOT NULL"
            )
        ).all() == [("ST_MultiPolygon", 2154, True)] * 2
        assert connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname = :schema AND indexname = 'sidx_risques_sup_geom'"
            ),
            {"schema": schema},
        ).scalar_one().endswith("USING gist (geom)")


def test_non_polygonal_geometry_rolls_back_conversion(postgis_database) -> None:
    """Vérifie qu'une géométrie non polygonale reste intacte après l'échec."""
    engine, schema = postgis_database
    with engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE TABLE {schema}.risques_sup (geom geometry(GEOMETRY, 2154))"
            )
        )
        connection.execute(
            text(
                f"INSERT INTO {schema}.risques_sup "
                "VALUES (ST_SetSRID(ST_Point(700000, 6600000), 2154))"
            )
        )
    with pytest.raises(DataError):
        import_sup.add_geometry_column_to_table.fn(schema=schema)
    with engine.connect() as connection:
        assert connection.execute(
            text(f"SELECT ST_GeometryType(geom) FROM {schema}.risques_sup")
        ).scalar_one() == "ST_Point"
        assert connection.execute(
            text(
                "SELECT type FROM geometry_columns "
                "WHERE f_table_schema = :schema AND f_table_name = 'risques_sup'"
            ),
            {"schema": schema},
        ).scalar_one() == "GEOMETRY"
