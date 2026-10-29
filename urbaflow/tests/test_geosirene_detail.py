"""Tests de l'enrichissement des établissements par les unités légales."""

import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import duckdb
import pytest
from flows.geosirene.import_sirene_etablissement import (
    create_geosirene_etablissement_detail,
    create_geosirene_etablissement_detail_table,
)
from flows.geosirene.import_sirene_unite_legale import (
    fetch_sirene_unite_legale_parquet,
    load_sirene_unite_legale,
)
from shared_tasks.duckdb_utils import get_parquet_schema
from sqlalchemy import create_engine, text

DETAIL_MODULE = "flows.geosirene.import_sirene_etablissement"
LEGAL_MODULE = "flows.geosirene.import_sirene_unite_legale"


@pytest.fixture
def database():
    """Crée un schéma isolé avec plusieurs établissements et géolocalisations."""
    url = os.environ.get("SIRENE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("SIRENE_TEST_DATABASE_URL non définie pour les tests PostgreSQL.")
    engine = create_engine(url)
    schema = f"test_sirene_{uuid4().hex[:12]}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(
            text(
                f"""
                CREATE TABLE "{schema}".sirene_etablissement (
                    siret text PRIMARY KEY, siren text,
                    denomination_usuelle_etablissement text,
                    enseigne1_etablissement text, enseigne2_etablissement text,
                    enseigne3_etablissement text
                );
                INSERT INTO "{schema}".sirene_etablissement VALUES
                    ('48866938300025', '488669383', NULL, NULL, NULL, NULL),
                    ('48866938300033', '488669383', ' Boutique ', 'PIZZERIA ENZO',
                        ' ', '[ND]'),
                    ('00000000100001', '000000001', NULL, 'Sans unité', NULL, NULL),
                    ('00000000200001', '000000002', NULL, NULL, NULL, NULL);
                CREATE TABLE "{schema}".geosirene_etablissement (
                    siret text PRIMARY KEY, geom point
                );
                INSERT INTO "{schema}".geosirene_etablissement
                    SELECT siret, point(1, 2)
                    FROM "{schema}".sirene_etablissement;
                INSERT INTO "{schema}".geosirene_etablissement VALUES
                    ('99999999900001', point(1, 2));
                """
            )
        )
    try:
        with (
            patch(f"{DETAIL_MODULE}.create_engine", return_value=engine),
            patch(f"{LEGAL_MODULE}.create_engine", return_value=engine),
        ):
            yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


@pytest.fixture
def legal_parquet(tmp_path: Path):
    """Produit un stock avec doublons usuels, valeur masquée et SIREN hors périmètre."""
    path = tmp_path / "unites.parquet"
    with duckdb.connect() as connection:
        connection.execute(
            """
            CREATE TABLE legal AS SELECT * FROM (VALUES
                ('488669383', 'FGM PIZZA', 'PIZZERIA ENZO', ' PIZZERIA ENZO ',
                    '[ND]', '5610A'),
                ('999999999', 'Hors périmètre', NULL, NULL, NULL, '0000Z')
            ) AS units(siren, denominationUniteLegale,
                denominationUsuelle1UniteLegale, denominationUsuelle2UniteLegale,
                denominationUsuelle3UniteLegale, activitePrincipaleUniteLegale)
            """
        )
        connection.execute("COPY legal TO ? (FORMAT PARQUET)", [str(path)])
    return path, get_parquet_schema.fn(path)


def test_detail_names_and_left_join(database, legal_parquet):
    """Conserve les établissements sans unité, les attributs et les noms dédupliqués."""
    engine, schema = database
    path, columns = legal_parquet
    assert load_sirene_unite_legale.fn(path, columns, db_schema=schema) == 1
    create_geosirene_etablissement_detail_table.fn(db_schema=schema)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"SELECT siret, denomination_unite_legale, noms_usuels, "
                f"unite_legale_activite_principale_unite_legale, "
                f'sirene_siren FROM "{schema}".geosirene_detail ORDER BY siret'
            )
        ).fetchall()
        assert len(rows) == 4
        by_siret = {row[0]: row for row in rows}
        assert by_siret["48866938300025"][1:] == (
            "FGM PIZZA",
            ["PIZZERIA ENZO"],
            "5610A",
            "488669383",
        )
        assert by_siret["48866938300033"][2] == ["PIZZERIA ENZO", "Boutique"]
        assert by_siret["00000000100001"][1:3] == (None, ["Sans unité"])
        assert by_siret["00000000200001"][1:3] == (None, [])
        assert (
            connection.scalar(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = 'geosirene_detail' "
                    "AND column_name = 'noms_usuels'"
                ),
                {"schema": schema},
            )
            == "ARRAY"
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE schemaname = :schema "
                    "AND tablename = 'geosirene_detail'"
                ),
                {"schema": schema},
            )
            == 2
        )
    create_geosirene_etablissement_detail_table.fn(db_schema=schema, recreate=False)
    create_geosirene_etablissement_detail_table.fn(
        db_schema=schema, detail_table_name="ancien_detail"
    )


def test_legal_replacement_and_rollback(database, legal_parquet):
    """Remplace sans doublons et annule les mutations si le chargement échoue."""
    engine, schema = database
    path, columns = legal_parquet
    for recreate in (True, False):
        assert (
            load_sirene_unite_legale.fn(
                path, columns, db_schema=schema, recreate=recreate, chunk_size=1
            )
            == 1
        )
    with (
        patch(f"{LEGAL_MODULE}.load", side_effect=RuntimeError("Erreur de chargement")),
        pytest.raises(RuntimeError, match="Erreur de chargement"),
    ):
        load_sirene_unite_legale.fn(path, columns, db_schema=schema)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(f'SELECT count(*) FROM "{schema}".sirene_unite_legale')
            )
            == 1
        )


def test_missing_units_does_not_destroy_existing_detail(database):
    """Signale le prérequis manquant avant de remplacer une table existante."""
    engine, schema = database
    with engine.begin() as connection:
        connection.execute(
            text(f'CREATE TABLE "{schema}".geosirene_detail AS SELECT 42 AS marker')
        )
    with pytest.raises(ValueError, match="sirene-unite-legale"):
        create_geosirene_etablissement_detail_table.fn(db_schema=schema)
    with engine.connect() as connection:
        assert (
            connection.scalar(text(f'SELECT marker FROM "{schema}".geosirene_detail'))
            == 42
        )


def test_legal_incremental_import_preserves_other_sirens(database, legal_parquet):
    """Ne supprime pas les unités légales extérieures au périmètre actualisé."""
    engine, schema = database
    path, columns = legal_parquet
    load_sirene_unite_legale.fn(path, columns, db_schema=schema)
    with engine.begin() as connection:
        connection.execute(
            text(
                f'INSERT INTO "{schema}".sirene_unite_legale '
                "(siren, denomination_unite_legale) VALUES ('999999999', 'Conservée')"
            )
        )
    load_sirene_unite_legale.fn(path, columns, db_schema=schema, recreate=False)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(f'SELECT count(*) FROM "{schema}".sirene_unite_legale')
            )
            == 2
        )


def test_no_matching_units_rolls_back(database, legal_parquet):
    """Une source sans correspondance ne remplace pas les unités déjà chargées."""
    engine, schema = database
    path, columns = legal_parquet
    load_sirene_unite_legale.fn(path, columns, db_schema=schema)
    with engine.begin() as connection:
        connection.execute(
            text(
                f'DELETE FROM "{schema}".sirene_etablissement '
                "WHERE siren = '488669383'"
            )
        )
    with pytest.raises(ValueError, match="Aucune unité légale"):
        load_sirene_unite_legale.fn(path, columns, db_schema=schema)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(f'SELECT count(*) FROM "{schema}".sirene_unite_legale')
            )
            == 1
        )


def test_legal_import_loads_multiple_chunks(database, tmp_path):
    """Vérifie le chargement au-delà d'un vecteur DuckDB de 2048 lignes."""
    engine, schema = database
    path = tmp_path / "many_units.parquet"
    with engine.begin() as connection:
        connection.execute(
            text(
                f'INSERT INTO "{schema}".sirene_etablissement (siret, siren) '
                "SELECT lpad(n::text, 9, '0') || '00001', lpad(n::text, 9, '0') "
                "FROM generate_series(100, 2199) AS n"
            )
        )
    with duckdb.connect() as connection:
        connection.execute(
            """
            COPY (SELECT lpad(n::varchar, 9, '0') AS siren,
                'Dénomination ' || n::varchar AS denominationUniteLegale
                FROM range(100, 2200) AS series(n)) TO ? (FORMAT PARQUET)
            """,
            [str(path)],
        )
    from shared_tasks.etl_gpd_utils import load

    with patch(f"{LEGAL_MODULE}.load", wraps=load) as loader:
        assert (
            load_sirene_unite_legale.fn(
                path, get_parquet_schema.fn(path), db_schema=schema, chunk_size=2048
            )
            == 2100
        )
    assert loader.call_count == 2
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(f'SELECT count(*) FROM "{schema}".sirene_unite_legale')
            )
            == 2100
        )


def test_empty_perimeter_is_rejected(database, legal_parquet):
    """Refuse le périmètre vide plutôt que de charger tout le stock national."""
    engine, schema = database
    with engine.begin() as connection:
        connection.execute(text(f'DELETE FROM "{schema}".sirene_etablissement'))
    with pytest.raises(ValueError, match="Aucun SIREN"):
        load_sirene_unite_legale.fn(*legal_parquet, db_schema=schema)


def test_fetch_local_parquet(legal_parquet):
    """Utilise le stock local fourni sans téléchargement."""
    path, _ = legal_parquet
    assert fetch_sirene_unite_legale_parquet.fn(path.parent) == path


def test_detail_flow_forwards_legal_table():
    """Transmet le nom personnalisé de la table des unités légales."""
    with patch(
        f"{DETAIL_MODULE}.create_geosirene_etablissement_detail_table"
    ) as create:
        create_geosirene_etablissement_detail.fn(
            db_schema="test", unite_legale_table_name="legal"
        )
    assert create.call_args.kwargs["unite_legale_table_name"] == "legal"
    assert create.call_args.kwargs["detail_table_name"] == "geosirene_detail"


@pytest.mark.parametrize(
    ("command", "flow_name"),
    [
        ("sirene-unite-legale", "import_sirene_unite_legale_data"),
        ("geosirene-detail", "create_geosirene_etablissement_detail"),
    ],
)
def test_cli_legal_table_options(command, flow_name):
    """Vérifie le câblage CLI, le schéma et les noms personnalisés."""
    from cli.app import app
    from typer.testing import CliRunner

    option = (
        "--table-name"
        if command == "sirene-unite-legale"
        else ("--unite-legale-table-name")
    )
    with patch(f"cli.commands.geosirene.{flow_name}") as flow:
        result = CliRunner().invoke(
            app, [command, "--schema", "test", option, "legal", "--no-recreate"]
        )
    assert result.exit_code == 0, result.output
    assert flow.call_args.kwargs["db_schema"] == "test"
    assert flow.call_args.kwargs["recreate"] is False
    key = (
        "table_name" if command == "sirene-unite-legale" else "unite_legale_table_name"
    )
    assert flow.call_args.kwargs[key] == "legal"
