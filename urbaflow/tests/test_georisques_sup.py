"""Vérifie le typage PostGIS de la colonne géométrique des SUP."""

from unittest.mock import MagicMock

import pytest
from flows.georisques import import_sup
from sqlalchemy.dialects import postgresql


def test_geometry_column_uses_multipolygon_and_converts_existing_values(
    monkeypatch,
) -> None:
    """Vérifie la création typée et la conversion des colonnes existantes."""
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.engine.dialect = postgresql.dialect()
    monkeypatch.setattr(import_sup, "create_engine", lambda: engine)

    import_sup.add_geometry_column_to_table.fn(
        schema="schema-sup", table_name="risques_Sup"
    )

    statement = str(connection.execute.call_args.args[0])
    assert statement.count('ALTER TABLE "schema-sup"."risques_Sup"') == 2
    assert "geom geometry(MULTIPOLYGON, 2154)" in statement
    assert "ALTER COLUMN geom TYPE geometry(MULTIPOLYGON, 2154)" in statement
    assert "USING ST_Multi(geom)" in statement
    assert 'CREATE INDEX IF NOT EXISTS "sidx_risques_Sup_geom"' in statement
    assert 'ON "schema-sup"."risques_Sup" USING GIST (geom)' in statement
    engine.begin.assert_called_once_with()


def test_geometry_conversion_propagates_database_errors(monkeypatch) -> None:
    """Vérifie qu'une géométrie incompatible fait échouer la transaction."""
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.engine.dialect = postgresql.dialect()
    error = RuntimeError("Géométrie non polygonale")
    connection.execute.side_effect = error
    monkeypatch.setattr(import_sup, "create_engine", lambda: engine)

    with pytest.raises(RuntimeError, match="Géométrie non polygonale"):
        import_sup.add_geometry_column_to_table.fn()

    transaction_exit = engine.begin.return_value.__exit__.call_args
    assert transaction_exit.args[1] is error
