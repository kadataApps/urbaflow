"""Tests de lecture GeoParquet et de chargement des contours DGFiP."""

import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import duckdb
import pytest
from flows.cadastre.import_dgfip_geoparquet import (
    ATTRIBUTE_COLUMNS,
    OBJECT_TABLES,
    build_perimeter_filter,
    import_dgfip_geoparquet_flow,
    load_cadastre,
    open_cadastre_source,
)
from shapely.geometry import Polygon
from shared_tasks.geopf_utils import Perimeter, resolve_perimeter
from sqlalchemy import create_engine, text

MODULE = "flows.cadastre.import_dgfip_geoparquet"


@pytest.fixture
def parquet_path(tmp_path: Path) -> Path:
    """Crée un fichier représentatif incluant Corse, outre-mer et objets exclus."""
    path = tmp_path / "cadastre.parquet"
    with duckdb.connect() as connection:
        attributes = ", ".join(
            f'"{source}" {column_type}' for source, _, column_type in ATTRIBUTE_COLUMNS
        )
        connection.execute(
            f"CREATE TABLE cadastre (type_objet VARCHAR, {attributes}, geometry BLOB)"
        )
        geometry = Polygon(
            [(350000, 6750000), (350100, 6750000), (350100, 6750100), (350000, 6750000)]
        ).wkb
        for commune, department, srid in (
            ("35001", "35", 2154),
            ("35002", "35", 2154),
            ("2A004", "2A", 2154),
            ("97411", "974", 2975),
            ("97201", "972", 5490),
        ):
            for object_type in (*OBJECT_TABLES, "parcelles"):
                values = {
                    "commune": commune,
                    "departement": department,
                    "nom": "Contour de test",
                    "geom_srid": srid,
                }
                row = [object_type]
                row.extend(values.get(column[0]) for column in ATTRIBUTE_COLUMNS)
                row.append(geometry)
                connection.execute(
                    "INSERT INTO cadastre VALUES (" + ", ".join("?" for _ in row) + ")",
                    row,
                )
        connection.execute("COPY cadastre TO ? (FORMAT PARQUET)", [str(path)])
    return path


@pytest.mark.parametrize(
    ("perimeter", "expected_codes"),
    [
        (None, {"35001", "35002", "2A004", "97411", "97201"}),
        (Perimeter(("35",), None), {"35001", "35002"}),
        (Perimeter(("35",), ("35001",)), {"35001"}),
        (Perimeter(("2A",), None), {"2A004"}),
        (Perimeter(("974",), None), {"97411"}),
        (Perimeter(("972",), None), {"97201"}),
        (Perimeter(("35", "974"), None), {"35001", "35002", "97411"}),
    ],
)
def test_read_filtered_source(parquet_path, perimeter, expected_codes):
    """Vérifie les filtres réels, les trois types d'objets et la lecture WKB."""
    with open_cadastre_source(str(parquet_path), perimeter) as connection:
        rows = connection.fetchall()
    assert {row[3] for row in rows} == expected_codes
    assert {row[0] for row in rows} == set(OBJECT_TABLES)
    assert len(rows) == len(expected_codes) * 3
    assert all(isinstance(row[-1], bytes) for row in rows)


@pytest.mark.parametrize(
    "perimeter",
    [
        Perimeter((), None),
        Perimeter(("35",), ()),
        Perimeter(("35'; DROP TABLE x",), None),
        Perimeter(("35",), ("35001' OR TRUE",)),
    ],
)
def test_reject_invalid_perimeter(perimeter):
    """Refuse les périmètres vides ou mal formés avant toute mutation."""
    with pytest.raises(ValueError, match="Codes de périmètre invalides"):
        build_perimeter_filter(perimeter)


def test_resolve_epci_and_normalize_codes():
    """Réutilise la résolution EPCI existante et normalise les codes INSEE."""
    with patch(
        "shared_tasks.geopf_utils.fetch_epci_communes",
        return_value=[{"code": "35001"}, {"code": "35002"}],
    ) as fetch:
        perimeter = resolve_perimeter(epci="243500139")
    fetch.assert_called_once_with("243500139")
    assert perimeter == Perimeter(("35",), ("35001", "35002"))
    assert resolve_perimeter(communes="1001,2a004,97411").insee_codes == (
        "01001",
        "2A004",
        "97411",
    )


def test_conflicting_filters_do_not_open_source():
    """Refuse des filtres concurrents avant toute lecture ou connexion cible."""
    with (
        patch(f"{MODULE}.open_cadastre_source") as open_source,
        pytest.raises(ValueError, match="Un seul périmètre"),
    ):
        import_dgfip_geoparquet_flow.fn(departements="35", communes="35001")
    open_source.assert_not_called()


@pytest.mark.parametrize(
    ("option", "value", "argument"),
    [
        ("--communes", "35001,35002", "communes"),
        ("--epci", "243500139", "epci"),
        ("--departement", "35,22", "departements"),
    ],
)
def test_cli_perimeter_and_schema(monkeypatch, option, value, argument):
    """Vérifie le routage Typer et la configuration du schéma par environnement."""
    from cli.app import app
    from typer.testing import CliRunner

    monkeypatch.setenv("IMPORT_SCHEMA", "cadastre_test")
    expected_arguments = {
        "departements": None,
        "epci": None,
        "communes": None,
        "db_schema": "cadastre_test",
        "source": "local.parquet",
        argument: value,
    }
    with patch("cli.commands.cadastre.import_dgfip_geoparquet_flow") as import_flow:
        result = CliRunner().invoke(
            app, ["dgfip-geoparquet", option, value, "--source", "local.parquet"]
        )
    assert result.exit_code == 0, result.output
    import_flow.assert_called_once_with(**expected_arguments)


@pytest.fixture
def database():
    """Isole les tests PostGIS dans un schéma supprimé après chaque test."""
    url = os.environ.get("DGFIP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("DGFIP_TEST_DATABASE_URL non définie pour les tests PostGIS.")
    engine = create_engine(url)
    schema = f"test_dgfip_{uuid4().hex[:12]}"
    try:
        yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def read_counts(engine, schema):
    """Compte les lignes présentes dans chacune des trois tables cibles."""
    with engine.connect() as connection:
        return {
            object_type: connection.scalar(
                text(f'SELECT count(*) FROM "{schema}".{table}')
            )
            for object_type, table in OBJECT_TABLES.items()
        }


@pytest.mark.parametrize("selection", ["communes", "departements", "epci"])
def test_postgis_replacement_and_geometry(parquet_path, database, selection):
    """Vérifie lots, reprojection par objet, index et réimport sans doublons."""
    engine, schema = database
    with (
        patch(f"{MODULE}.create_engine", return_value=engine),
        patch(f"{MODULE}.BATCH_SIZE", 2),
    ):
        counts = import_dgfip_geoparquet_flow.fn(
            db_schema=schema, source=str(parquet_path)
        )
        assert counts == dict.fromkeys(OBJECT_TABLES, 5)
        expected_count = 1 if selection == "communes" else 2
        selected_value = {
            "communes": "35001",
            "departements": "35",
            "epci": "243500139",
        }[selection]
        with patch(
            "shared_tasks.geopf_utils.fetch_epci_communes",
            return_value=[{"code": "35001"}, {"code": "35002"}],
        ):
            assert import_dgfip_geoparquet_flow.fn(
                **{selection: selected_value},
                db_schema=schema,
                source=str(parquet_path),
            ) == dict.fromkeys(OBJECT_TABLES, expected_count)
    assert read_counts(engine, schema) == dict.fromkeys(OBJECT_TABLES, 5)
    with engine.connect() as connection:
        for table in OBJECT_TABLES.values():
            rows = connection.execute(
                text(
                    f"SELECT ST_SRID(geom), ST_GeometryType(geom), "
                    f'ST_IsValid(geom), id, geom_srid FROM "{schema}".{table}'
                )
            ).fetchall()
            assert len(rows) == 5
            assert all(row[:4] == (2154, "ST_MultiPolygon", True, None) for row in rows)
            assert {row[4] for row in rows} == {2154, 2975, 5490}
        assert (
            connection.scalar(
                text("SELECT count(*) FROM pg_indexes WHERE schemaname = :schema"),
                {"schema": schema},
            )
            == 12
        )


def test_postgis_rollback_on_failure_or_empty_source(parquet_path, database):
    """Vérifie qu'aucune table n'est vidée si l'import échoue après suppression."""
    engine, schema = database
    with patch(f"{MODULE}.create_engine", return_value=engine):
        import_dgfip_geoparquet_flow.fn(db_schema=schema, source=str(parquet_path))
        with (
            open_cadastre_source(str(parquet_path), None) as source,
            patch(f"{MODULE}.execute_values", side_effect=RuntimeError("Erreur SQL")),
            pytest.raises(RuntimeError, match="Erreur SQL"),
        ):
            load_cadastre(source, schema, None)
        assert read_counts(engine, schema) == dict.fromkeys(OBJECT_TABLES, 5)
        with duckdb.connect() as source:
            source.execute("SELECT NULL WHERE FALSE")
            with pytest.raises(ValueError, match="Aucun contour"):
                load_cadastre(source, schema, None)
        assert read_counts(engine, schema) == dict.fromkeys(OBJECT_TABLES, 5)


def test_postgis_rollback_on_missing_srid(parquet_path, database):
    """Refuse une géométrie sans SRID source sans perdre les anciennes données."""
    engine, schema = database
    with patch(f"{MODULE}.create_engine", return_value=engine):
        import_dgfip_geoparquet_flow.fn(db_schema=schema, source=str(parquet_path))
        with duckdb.connect() as source:
            source.execute(
                "SELECT 'communes', "
                + ", ".join("NULL" for _ in range(len(ATTRIBUTE_COLUMNS) + 1))
            )
            with pytest.raises(ValueError, match="geom_srid absent"):
                load_cadastre(source, schema, None)
        assert read_counts(engine, schema) == dict.fromkeys(OBJECT_TABLES, 5)
