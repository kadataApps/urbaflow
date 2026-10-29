"""Tests de la colonne MultiPolygon des données SIS."""

import os
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from flows.georisques import import_sis
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql


def test_geometry_column_ddl(monkeypatch):
    """Vérifie le type imposé, la migration et la protection des identifiants."""
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.engine.dialect = postgresql.dialect()
    monkeypatch.setattr(import_sis, "create_engine", lambda: engine)

    import_sis.add_geometry_column_to_table.fn(
        schema="SIS schema", table_name="risques_Sis"
    )

    statement = str(connection.execute.call_args.args[0])
    assert 'ALTER TABLE "SIS schema"."risques_Sis"' in statement
    assert "geom geometry(MultiPolygon, 2154)" in statement
    assert "ALTER COLUMN geom TYPE geometry(MultiPolygon, 2154)" in statement
    assert "USING ST_Multi(geom)" in statement
    assert 'CREATE INDEX IF NOT EXISTS "sidx_risques_Sis_geom"' in statement


@pytest.fixture
def postgis_database(monkeypatch):
    """Crée un schéma isolé dans une base PostGIS explicitement dédiée aux tests."""
    database_url = os.environ.get("SIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("SIS_TEST_DATABASE_URL est requis.")
    engine = create_engine(database_url)
    schema = f"test_sis_{uuid4().hex[:12]}"
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    monkeypatch.setattr(import_sis, "create_engine", lambda: engine)
    try:
        yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        engine.dispose()


@pytest.mark.parametrize("existing_column", [False, True])
def test_multipolygon_column_in_postgis(postgis_database, existing_column):
    """Valide création, migration sans perte, reprojection et appels répétés."""
    engine, schema = postgis_database
    import_sis.create_table_sis.fn(schema=schema, recreate=False)
    if existing_column:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    ALTER TABLE {schema}.risques_sis
                        ADD COLUMN geom geometry(GEOMETRY, 2154);
                    INSERT INTO {schema}.risques_sis (identifiant_ssp, geom)
                    VALUES
                        ('existing_polygon', ST_GeomFromText(
                            'POLYGON((0 0, 1 0, 1 1, 0 0))', 2154)),
                        ('existing_multi', ST_GeomFromText(
                            'MULTIPOLYGON(((0 0, 1 0, 1 1, 0 0)))', 2154)),
                        ('existing_null', NULL);
                    """
                )
            )

    import_sis.add_geometry_column_to_table.fn(schema=schema)
    import_sis.add_geometry_column_to_table.fn(schema=schema)

    with engine.begin() as connection:
        column_type = connection.execute(
            text(
                """
                SELECT type, srid
                FROM geometry_columns
                WHERE f_table_schema = :schema
                    AND f_table_name = 'risques_sis'
                    AND f_geometry_column = 'geom'
                """
            ),
            {"schema": schema},
        ).one()
        assert tuple(column_type) == ("MULTIPOLYGON", 2154)
        if existing_column:
            existing_rows = connection.execute(
                text(
                    f"""
                    SELECT identifiant_ssp, ST_GeometryType(geom), ST_Area(geom)
                    FROM {schema}.risques_sis ORDER BY identifiant_ssp
                    """
                )
            ).all()
            assert [tuple(row) for row in existing_rows] == [
                ("existing_multi", "ST_MultiPolygon", 0.5),
                ("existing_null", None, None),
                ("existing_polygon", "ST_MultiPolygon", 0.5),
            ]
        connection.execute(
            text(
                f"""
                INSERT INTO {schema}.risques_sis (identifiant_ssp, bbox_geojson)
                VALUES
                    ('polygon', '{{"type": "Polygon", "coordinates":
                        [[[200000, 6000000], [200100, 6000000],
                          [200100, 6000100], [200000, 6000000]]]}}'),
                    ('multipolygon', '{{"type": "MultiPolygon", "coordinates":
                        [[[[200000, 6000000], [200100, 6000000],
                           [200100, 6000100], [200000, 6000000]]]]}}'),
                    ('null', NULL), ('empty', '');
                """
            )
        )

    import_sis.populate_geom.fn(schema=schema)

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT identifiant_ssp, ST_GeometryType(geom), ST_SRID(geom),
                    ST_IsValid(geom)
                FROM {schema}.risques_sis
                WHERE identifiant_ssp IN ('polygon', 'multipolygon', 'null', 'empty')
                ORDER BY identifiant_ssp
                """
            )
        ).all()
        assert [tuple(row) for row in rows] == [
            ("empty", None, None, None),
            ("multipolygon", "ST_MultiPolygon", 2154, True),
            ("null", None, None, None),
            ("polygon", "ST_MultiPolygon", 2154, True),
        ]
        assert (
            connection.execute(
                text(
                    """
                SELECT count(*) FROM pg_indexes
                WHERE schemaname = :schema AND tablename = 'risques_sis'
                    AND indexname = 'sidx_risques_sis_geom'
                """
                ),
                {"schema": schema},
            ).scalar_one()
            == 1
        )
