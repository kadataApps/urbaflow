"""Validation PostGIS activée par MAJIC_TEST_DATABASE_URL."""

import os
import shutil
from uuid import uuid4

import pytest
import sqlalchemy as sa
from flows.cadastre.tasks import (
    clean_after_imports,
    format_cadastre,
    format_majic,
    merge_majic_cadastre,
    move_data_to_import_schema,
)
from flows.cadastre.tasks.create_unites_foncieres import flow_create_unites_foncieres
from flows.cadastre.tasks.get_communes_majic import get_imported_communes_from_postgres
from flows.cadastre.tasks.import_majic import import_majic_files
from shared_tasks.config import QUERIES_DIR
from shared_tasks.db_engine import create_engine, quote_identifier
from shared_tasks.db_sql_utils import run_sql_script


def test_consolidated_results_survive_work_schema_deletion(monkeypatch, tmp_path):
    """Exécute le traitement et conserve les résultats après suppression de MAJIC."""
    database_url = os.environ.get("MAJIC_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("MAJIC_TEST_DATABASE_URL est requis pour la validation PostGIS.")
    engine = sa.create_engine(database_url)
    suffix = uuid4().hex
    import_schema = f"test_import_{suffix}"
    work_schema = f"test_majic_{suffix}"
    target = quote_identifier(import_schema)
    source = quote_identifier(work_schema)
    connection_url = engine.url
    environment = {
        "POSTGRES_HOST": connection_url.host,
        "POSTGRES_PORT": str(connection_url.port or 5432),
        "POSTGRES_DB": connection_url.database,
        "POSTGRES_USER": connection_url.username,
        "POSTGRES_PASS": connection_url.password or "",
        "IMPORT_SCHEMA": import_schema,
        "MAJIC_SCHEMA": work_schema,
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    shutil.copytree(QUERIES_DIR / "majic", tmp_path / "sql")
    for module in (
        format_majic,
        format_cadastre,
        merge_majic_cadastre,
        move_data_to_import_schema,
    ):
        monkeypatch.setattr(module, "TEMP_DIR", tmp_path)
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    destination_engine = create_engine()
    work_engine = create_engine(schema=work_schema)

    try:
        with destination_engine.begin() as connection:
            run_sql_script(
                connection=connection,
                sql_filepath=QUERIES_DIR / "dgfip_topo/create_dgfip_topo.sql",
            )
            connection.exec_driver_sql(
                "CREATE TABLE parcelle (marker text); "
                "INSERT INTO parcelle VALUES ('import préservé'); "
                "INSERT INTO voie_france (idvoie, natvoi, libvoi) "
                "VALUES ('330630001', 'RUE', 'DE TEST'); "
                "INSERT INTO commune_france (idcom, libcom) "
                "VALUES ('33063', 'Bordeaux');"
            )
        import_majic_files(data_directory)
        format_majic.clean_with_drop_db_for_majic_import()
        format_majic.init_db_for_majic_import()
        format_majic.execute_format_majic_scripts()
        format_cadastre.execute_init_cadastre()
        with work_engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO parcelle "
                "(parcelle, ccodep, ccodir, ccocom, dnupro, dcntpa, ccoriv, dnvoiri) "
                "VALUES ('330063000AB0001', '33', '0', '063', '00001', 100, "
                "'0001', '0001'); "
                "INSERT INTO cadastre_parcelles "
                "(commune, prefixe, section, numero, wkb_geometry) "
                "VALUES ('33063', '000', 'AB', '0001', "
                "ST_GeomFromText('MULTIPOLYGON(((700000 6600000, "
                "700100 6600000, 700100 6600100, 700000 6600100, "
                "700000 6600000)))', 2154));"
            )
        format_cadastre.execute_format_cadastre()
        assert get_imported_communes_from_postgres()["code_insee"].to_list() == [
            "33063"
        ]
        for _ in range(2):
            merge_majic_cadastre.execute_merge_cadastre_majic_scripts()
            flow_create_unites_foncieres()
        move_data_to_import_schema.flow_import_parcelles()
        move_data_to_import_schema.flow_import_proprietaire()
        move_data_to_import_schema.flow_import_local()
        format_cadastre.execute_init_bati()
        format_cadastre.execute_init_sections()
        with work_engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO cadastre_bati (commune) VALUES ('33063'); "
                "INSERT INTO cadastre_sections (id, commune) "
                "VALUES ('33063000AB', '33063');"
            )
        move_data_to_import_schema.flow_import_bati()
        move_data_to_import_schema.flow_import_sections()

        with engine.connect() as connection:
            assert (
                connection.scalar(
                    sa.text(
                        f"SELECT count(*) FROM {target}.parcellaire "
                        "WHERE libcom = 'Bordeaux' AND dlibvoi = 'RUE DE TEST'"
                    )
                )
                == 1
            )
            assert (
                connection.scalar(
                    sa.text("SELECT to_regclass(:table)"),
                    {"table": f"{work_schema}.parcellaire"},
                )
                is None
            )

        clean_after_imports.clean_db()
        clean_after_imports.clean_db()

        with engine.connect() as connection:
            assert (
                connection.scalar(
                    sa.text(
                        "SELECT count(*) FROM pg_namespace WHERE nspname = :schema"
                    ),
                    {"schema": work_schema},
                )
                == 0
            )
            for table, count in (
                ("parcellaire", 1),
                ("unites_foncieres", 1),
                ("parcellaire_france", 1),
                ("proprietaire_droit", 0),
                ("pb0010_local", 0),
                ("bati_france", 1),
                ("sections_cadastrales_france", 1),
            ):
                assert (
                    connection.scalar(sa.text(f"SELECT count(*) FROM {target}.{table}"))
                    == count
                )
            assert (
                connection.scalar(sa.text(f"SELECT marker FROM {target}.parcelle"))
                == "import préservé"
            )
            assert (
                connection.scalar(
                    sa.text(
                        f"SELECT ST_IsValid(geom) AND id_uf IS NOT NULL "
                        f"FROM {target}.parcellaire"
                    )
                )
                is True
            )
            expected_indexes = [
                "parcellaire_pkey",
                "parcellaire_geom_idx",
                "parcellaire_geom_centroid_sidx",
                "unites_foncieres_pkey",
                "unites_foncieres_geom_sidx",
            ]
            assert connection.scalar(
                sa.text(
                    "SELECT count(*) FROM pg_indexes "
                    "WHERE schemaname = :schema AND indexname = ANY(:indexes)"
                ),
                {"schema": import_schema, "indexes": expected_indexes},
            ) == len(expected_indexes)
            assert (
                connection.scalar(
                    sa.text(
                        f"SELECT nextval(pg_get_serial_sequence("
                        f"'{import_schema}.unites_foncieres', 'id_uf'))"
                    )
                )
                == 2
            )
    finally:
        destination_engine.dispose()
        work_engine.dispose()
        with engine.begin() as connection:
            connection.exec_driver_sql(
                f"DROP SCHEMA IF EXISTS {source} CASCADE; "
                f"DROP SCHEMA IF EXISTS {target} CASCADE;"
            )
        engine.dispose()
