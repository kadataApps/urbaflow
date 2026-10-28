"""Vérifie le routage des tables et la protection des schémas persistants."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from flows.cadastre.tasks import (
    clean_after_imports,
    download_cadastre,
    import_majic,
    move_data_to_import_schema,
)
from flows.locomvac import import_locomvac
from flows.lovac import import_lovac
from shared_tasks import db_engine, etl_ogr_utils
from shared_tasks.config import db_schema, majic_schema


def test_default_schemas(monkeypatch):
    """Conserve public par défaut et isole les données de travail MAJIC."""
    monkeypatch.delenv("IMPORT_SCHEMA", raising=False)
    monkeypatch.delenv("MAJIC_SCHEMA", raising=False)
    assert db_schema() == "public"
    assert majic_schema() == "majic"


@pytest.mark.parametrize(
    "schema", ["", "public", "imports", "pg_catalog", "information_schema"]
)
def test_unsafe_majic_schema_is_rejected(monkeypatch, schema):
    """Refuse de nettoyer un schéma persistant ou système."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    monkeypatch.setenv("MAJIC_SCHEMA", schema)
    with pytest.raises(ValueError, match="MAJIC_SCHEMA"):
        majic_schema()


@pytest.mark.parametrize("explicit_schema", [None, 'MAJIC "travail"'])
def test_engine_configures_schema_without_overriding_options(
    monkeypatch, explicit_schema
):
    """Crée le schéma, protège son nom et préserve les options du moteur."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    connection = MagicMock(autocommit=False)
    cursor = connection.cursor.return_value.__enter__.return_value
    with (
        patch.object(db_engine.sa, "create_engine") as create_engine,
        patch.object(db_engine.sa.event, "listens_for") as listens_for,
    ):
        engine = db_engine.create_engine(schema=explicit_schema, pool_pre_ping=True)
        callback = listens_for.return_value.call_args.args[0]
        callback(connection, None)

    assert engine is create_engine.return_value
    assert create_engine.call_args.kwargs == {"pool_pre_ping": True}
    schema = db_engine.quote_identifier(explicit_schema or "imports")
    assert [call.args[0] for call in cursor.execute.call_args_list] == [
        f"CREATE SCHEMA IF NOT EXISTS {schema}",
        f"SET search_path TO {schema}, public",
    ]
    assert connection.autocommit is False


def test_schema_configuration_propagates_errors(monkeypatch):
    """Rend les erreurs SQL visibles et restaure le mode transactionnel."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    connection = MagicMock(autocommit=False)
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = RuntimeError("Droits insuffisants")
    with (
        patch.object(db_engine.sa, "create_engine"),
        patch.object(db_engine.sa.event, "listens_for") as listens_for,
    ):
        db_engine.create_engine()
        callback = listens_for.return_value.call_args.args[0]
        with pytest.raises(RuntimeError, match="Droits insuffisants"):
            callback(connection, None)
    assert connection.autocommit is False


@pytest.mark.parametrize(
    ("function_name", "source_schema", "source_table", "destination_table"),
    [
        (
            "insert_parcelles_to_import_schema",
            "imports",
            "parcellaire",
            "parcellaire_france",
        ),
        (
            "insert_proprietaire_to_import_schema",
            "majic",
            "proprietaire",
            "proprietaire_droit",
        ),
        ("insert_local_to_import_schema", "majic", "local10", "pb0010_local"),
        ("insert_bati_to_import_schema", "majic", "cadastre_bati", "bati_france"),
        (
            "insert_sections_to_import_schema",
            "majic",
            "cadastre_sections",
            "sections_cadastrales_france",
        ),
    ],
)
def test_exports_read_the_correct_schema(
    monkeypatch, function_name, source_schema, source_table, destination_table
):
    """Copie depuis MAJIC_SCHEMA, sauf le parcellaire déjà consolidé."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    monkeypatch.setenv("MAJIC_SCHEMA", "majic")
    with (
        patch.object(move_data_to_import_schema, "create_engine"),
        patch.object(move_data_to_import_schema, "run_sql_script") as run_sql,
    ):
        getattr(move_data_to_import_schema, function_name)()
    query = run_sql.call_args.kwargs["sql"]
    assert f'FROM "{source_schema}".{source_table};' in query
    assert f"INSERT INTO {destination_table} " in query
    assert "public." not in query


def test_cleanup_only_drops_work_schema(monkeypatch):
    """Ne supprime jamais IMPORT_SCHEMA lors du nettoyage final."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    monkeypatch.setenv("MAJIC_SCHEMA", 'MAJIC "travail"')
    with (
        patch.object(clean_after_imports, "create_engine"),
        patch.object(clean_after_imports, "run_sql_script") as run_sql,
    ):
        clean_after_imports.clean_db()
    assert run_sql.call_args.kwargs["sql"] == (
        'DROP SCHEMA IF EXISTS "MAJIC ""travail""" CASCADE;'
    )


def test_cleanup_preserves_import_schema_when_configuration_is_invalid(monkeypatch):
    """Interrompt le nettoyage avant toute requête si les schémas sont identiques."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    monkeypatch.setenv("MAJIC_SCHEMA", "imports")
    with (
        patch.object(clean_after_imports, "create_engine") as create_engine,
        pytest.raises(ValueError, match="MAJIC_SCHEMA"),
    ):
        clean_after_imports.clean_db()
    create_engine.assert_not_called()


def test_temporary_cleanup_is_limited_to_workflow_directories(monkeypatch, tmp_path):
    """Préserve les fichiers voisins des scripts et téléchargements temporaires."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(clean_after_imports, "TEMP_DIR", tmp_path / "scripts")
    for directory in ("scripts/sql", "temp/downloads"):
        (tmp_path / directory).mkdir(parents=True)
        (tmp_path / directory / "temporary.txt").write_text("temporaire")
    persistent_file = tmp_path / "temp/persistent.txt"
    persistent_file.write_text("à conserver")

    clean_after_imports.clean_temp_dir()

    assert not (tmp_path / "scripts/sql").exists()
    assert not (tmp_path / "temp/downloads").exists()
    assert persistent_file.read_text() == "à conserver"


def test_raw_majic_import_qualifies_tables(monkeypatch, tmp_path):
    """Charge les lignes brutes dans MAJIC_SCHEMA sans dépendre du search_path."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    monkeypatch.setenv("MAJIC_SCHEMA", "work")
    (tmp_path / "BATI.txt").write_text("330ligne de test\n")
    with (
        patch.object(import_majic, "create_engine") as create_engine,
        patch.object(import_majic, "run_sql_script") as run_sql,
    ):
        import_majic.import_majic_files(tmp_path)
    create_engine.assert_called_once_with(schema="work")
    queries = [call.kwargs["sql"] for call in run_sql.call_args_list]
    assert (
        'DROP TABLE IF EXISTS "work"."bati"; CREATE TABLE "work"."bati" (tmp text);'
    ) in queries
    assert 'INSERT INTO "work"."bati" VALUES (E\'330ligne de test\');' in queries


@pytest.mark.parametrize(
    ("task_name", "download_name", "table"),
    [
        ("download_cadastre_for_communes", "download_cadastre", "cadastre_parcelles"),
        ("download_bati_for_communes", "download_bati", "cadastre_bati"),
        ("download_sections_for_communes", "download_sections", "cadastre_sections"),
    ],
)
def test_cadastral_geometry_imports_use_work_schema(
    monkeypatch, task_name, download_name, table
):
    """Dirige les géométries de travail vers MAJIC_SCHEMA, pas IMPORT_SCHEMA."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    monkeypatch.setenv("MAJIC_SCHEMA", "work")
    with (
        patch.object(download_cadastre, download_name),
        patch.object(
            download_cadastre,
            "get_imported_communes_from_postgres",
            return_value=pd.DataFrame({"code_insee": ["33063"]}),
        ),
        patch.object(download_cadastre, "import_geojson") as import_geojson,
    ):
        getattr(download_cadastre, task_name)()
    assert import_geojson.call_args.args[1] == table
    assert import_geojson.call_args.kwargs == {"schema": "work"}


@pytest.mark.parametrize(
    ("module", "task_name"),
    [
        (import_lovac, "load_lovac_data"),
        (import_locomvac, "load_locomvac_data"),
    ],
)
def test_legacy_imports_use_import_schema(monkeypatch, module, task_name):
    """Applique également IMPORT_SCHEMA aux imports auparavant figés dans public."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    with (
        patch.object(module, "create_engine"),
        patch.object(module, "load") as load,
    ):
        getattr(module, task_name).fn(pd.DataFrame())
    assert load.call_args.kwargs["schema"] == "imports"


@pytest.mark.parametrize(
    ("command", "flow_name"),
    [
        (["risques-casias", "--departement", "33"], "import_risques_casias_flow"),
        (
            ["bdtopo-troncon-route", "--departement", "33"],
            "import_bdtopo_troncon_route_flow",
        ),
    ],
)
@pytest.mark.parametrize("explicit_schema", [None, "override"])
def test_cli_schema_respects_environment_and_explicit_override(
    monkeypatch, command, flow_name, explicit_schema
):
    """Priorise l'option explicite, puis IMPORT_SCHEMA, pour les imports du CLI."""
    import main
    from typer.testing import CliRunner

    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    arguments = command + (["--schema", explicit_schema] if explicit_schema else [])
    with patch.object(main, flow_name) as import_flow:
        result = CliRunner().invoke(main.app, arguments)
    assert result.exit_code == 0, result.output
    assert import_flow.call_args.kwargs["db_schema"] == (explicit_schema or "imports")


@pytest.mark.parametrize("schema", [None, "majic"])
def test_geojson_import_uses_requested_schema(monkeypatch, schema):
    """Transmet la destination à GDAL sans exposer le mot de passe au shell."""
    monkeypatch.setenv("IMPORT_SCHEMA", "imports")
    monkeypatch.setenv("POSTGRES_PASS", "mot-de-passe-test")
    with patch.object(etl_ogr_utils.subprocess, "run") as run:
        etl_ogr_utils.import_geojson("/data/parcelles.json", "parcelles", schema)
    command = run.call_args.args[0]
    assert command[command.index("-nln") + 1] == f"{schema or 'imports'}.parcelles"
    assert run.call_args.kwargs["check"] is True
    assert run.call_args.kwargs["env"]["PGPASSWORD"] == "mot-de-passe-test"
    assert all("mot-de-passe-test" not in argument for argument in command)


def test_geojson_import_propagates_errors():
    """Interrompt le traitement si la commande d'import GDAL échoue."""
    with (
        patch.object(
            etl_ogr_utils.subprocess,
            "run",
            side_effect=etl_ogr_utils.subprocess.CalledProcessError(1, ["ogr2ogr"]),
        ),
        pytest.raises(etl_ogr_utils.subprocess.CalledProcessError),
    ):
        etl_ogr_utils.import_geojson("/data/parcelles.json", "parcelles", "majic")
