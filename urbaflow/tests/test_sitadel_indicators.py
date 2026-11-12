import csv
import os
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from cli.app import app
from cli.commands import sitadel as sitadel_command
from flows.sitadel import enrich_commune
from shared_tasks.config import db_schema
from sqlalchemy import create_engine, inspect, text
from typer.testing import CliRunner


def housing_rows(code="01001", end_year=2025):
    """Produit dix années, avec des totaux incluant les résidences."""
    return [
        {
            "ANNEE": str(year),
            "COMM": code,
            "TYPE_LGT": housing_type,
            "LOG_COM": str(count),
            "LOG_AUT": "999",
        }
        for year in range(end_year - 9, end_year + 1)
        for housing_type, count in (
            ("Tous Logements", 10),
            ("Collectif", 3),
            ("Individuel pur", 2),
            ("Individuel groupe", 1),
            ("Residence", 4),
        )
    ]


def write_source(tmp_path, rows):
    """Écrit un export annuel SDES au format CSV avec BOM UTF-8."""
    path = tmp_path / "logements.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["ANNEE", "COMM", "TYPE_LGT", "LOG_COM", "LOG_AUT"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_counts_period_types_and_codes(tmp_path):
    """Respecte les bornes, les codes et les totaux incluant les résidences."""
    rows = [row for code in ("01001", "2A004", "97411") for row in housing_rows(code)]
    rows += housing_rows(end_year=2015) + housing_rows(end_year=2035)
    indicators = enrich_commune.read_housing_indicators(
        write_source(tmp_path, rows), 2025
    )

    assert {row["code_insee"] for row in indicators} == {"01001", "2A004", "97411"}
    for row in indicators:
        assert row["housing_created_10y"] == 100
        assert row["collective_housing_created_10y"] == 30
        assert row["individual_housing_created_10y"] == 30


@pytest.mark.parametrize("missing", ["blank", "year", "type"])
def test_incomplete_metric_is_null(tmp_path, missing):
    """Ne transforme pas une valeur ou un type manquant en zéro ou somme partielle."""
    rows = housing_rows()
    if missing == "blank":
        rows[1]["LOG_COM"] = ""
    elif missing == "year":
        rows.pop(1)
    else:
        rows = [row for row in rows if row["TYPE_LGT"] != "Collectif"]

    [indicator] = enrich_commune.read_housing_indicators(
        write_source(tmp_path, rows), 2025
    )

    assert indicator["collective_housing_created_10y"] is None
    assert indicator["housing_created_10y"] == 100
    assert indicator["individual_housing_created_10y"] == 30


def test_missing_individual_component_is_null(tmp_path):
    """Exige les deux sous-types individuels sur chacune des dix années."""
    rows = housing_rows()
    rows[3]["LOG_COM"] = ""
    [indicator] = enrich_commune.read_housing_indicators(
        write_source(tmp_path, rows), 2025
    )
    assert indicator["individual_housing_created_10y"] is None
    assert indicator["collective_housing_created_10y"] == 30


def test_explicit_zeros(tmp_path):
    """Conserve une série de zéros explicites comme un vrai total nul."""
    rows = housing_rows()
    for row in rows:
        row["LOG_COM"] = "0"
    [indicator] = enrich_commune.read_housing_indicators(
        write_source(tmp_path, rows), 2025
    )
    assert all(indicator[column] == 0 for column in enrich_commune.COUNT_COLUMNS)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ANNEE", "invalide"),
        ("COMM", "1001"),
        ("TYPE_LGT", "Autre"),
        ("LOG_COM", "nd"),
        ("LOG_COM", "-1"),
        ("LOG_COM", "1.5"),
    ],
)
def test_invalid_source_value(tmp_path, field, value):
    """Refuse les valeurs invalides au lieu de produire des indicateurs plausibles."""
    rows = housing_rows()
    rows[0][field] = value
    with pytest.raises(ValueError, match="invalide"):
        enrich_commune.read_housing_indicators(write_source(tmp_path, rows), 2025)


@pytest.mark.parametrize("problem", ["duplicate", "missing_year", "empty", "header"])
def test_invalid_source_shape(tmp_path, problem):
    """Refuse les doublons, les fichiers incomplets et les mauvais en-têtes."""
    rows = housing_rows()
    if problem == "duplicate":
        rows.append(rows[0].copy())
    elif problem == "missing_year":
        rows = [row for row in rows if row["ANNEE"] != "2025"]
    elif problem == "empty":
        rows = []
    path = write_source(tmp_path, rows)
    if problem == "header":
        path.write_text("COMM;LOG_AUT\n01001;42\n", encoding="utf-8")
    with pytest.raises(ValueError):
        enrich_commune.read_housing_indicators(path, 2025)


@pytest.mark.parametrize("local_source", [False, True])
def test_flow_source_and_default_period(monkeypatch, tmp_path, local_source):
    """Utilise le fichier fourni ou télécharge uniquement l'export annuel logements."""
    source_file = write_source(tmp_path, housing_rows(end_year=date.today().year - 1))
    download = MagicMock(return_value=source_file)
    monkeypatch.setattr(enrich_commune, "download_sitadel_file", download)
    monkeypatch.setattr(enrich_commune, "TEMP_DIR", tmp_path)
    read = MagicMock(side_effect=RuntimeError("Arrêt après lecture"))
    monkeypatch.setattr(enrich_commune, "read_housing_indicators", read)
    engine = MagicMock()
    monkeypatch.setattr(enrich_commune, "create_engine", engine)

    with pytest.raises(RuntimeError, match="Arrêt après lecture"):
        enrich_commune.enrich_commune_sitadel_flow.fn(
            source_file=source_file if local_source else None
        )

    read.assert_called_once_with(source_file, date.today().year - 1)
    engine.assert_not_called()
    if local_source:
        download.assert_not_called()
    else:
        download.assert_called_once_with(
            enrich_commune.ANNUAL_HOUSING_FILENAME, tmp_path / "sitadel"
        )


@pytest.mark.parametrize("end_year", [2010, date.today().year, 9999])
def test_invalid_period_before_download(monkeypatch, end_year):
    """Refuse les périodes non couvertes ou non révolues avant tout téléchargement."""
    download = MagicMock()
    monkeypatch.setattr(enrich_commune, "download_sitadel_file", download)
    with pytest.raises(ValueError, match="année"):
        enrich_commune.enrich_commune_sitadel_flow.fn(end_year=end_year)
    download.assert_not_called()


def test_cli_default_options(monkeypatch):
    """Transmet les paramètres par défaut au flow d'enrichissement."""
    run_flow = MagicMock()
    monkeypatch.setattr(sitadel_command, "enrich_commune_sitadel_flow", run_flow)

    result = CliRunner().invoke(app, ["sitadel-indicators"])

    assert result.exit_code == 0, result.output
    run_flow.assert_called_once()
    assert run_flow.call_args.kwargs == {
        "source_file": None,
        "db_schema": db_schema(),
        "table_name": "commune",
        "code_column": "code_insee",
        "population_column": "population",
        "end_year": None,
    }


def test_cli_custom_options(monkeypatch, tmp_path):
    """Transmet le fichier local, la période et les colonnes personnalisées."""
    source = write_source(tmp_path, housing_rows())
    run_flow = MagicMock()
    monkeypatch.setattr(sitadel_command, "enrich_commune_sitadel_flow", run_flow)

    result = CliRunner().invoke(
        app,
        [
            "sitadel-indicators",
            str(source),
            "--schema",
            "urbanisme",
            "--table-name",
            "banatic_communes",
            "--code-column",
            "insee",
            "--population-column",
            "pop_mun_commune",
            "--end-year",
            "2024",
        ],
    )

    assert result.exit_code == 0, result.output
    run_flow.assert_called_once_with(
        source_file=source,
        db_schema="urbanisme",
        table_name="banatic_communes",
        code_column="insee",
        population_column="pop_mun_commune",
        end_year=2024,
    )


@pytest.mark.parametrize("source_type", ["missing", "directory"])
def test_cli_rejects_invalid_source(monkeypatch, tmp_path, source_type):
    """Refuse une source inexistante ou un répertoire avant le flow."""
    run_flow = MagicMock()
    monkeypatch.setattr(sitadel_command, "enrich_commune_sitadel_flow", run_flow)
    source = tmp_path / "source"
    if source_type == "directory":
        source.mkdir()

    result = CliRunner().invoke(app, ["sitadel-indicators", str(source)])

    assert result.exit_code == 2, result.output
    run_flow.assert_not_called()


@pytest.mark.parametrize(
    ("code_column", "population_column"),
    [
        ("code_insee", "code_insee"),
        ("housing_created_10y", "population"),
        ("code_insee", enrich_commune.RATE_COLUMN),
    ],
)
def test_rejects_overlapping_columns(monkeypatch, code_column, population_column):
    """Empêche un indicateur d'écraser le code INSEE ou la population source."""
    download = MagicMock()
    monkeypatch.setattr(enrich_commune, "download_sitadel_file", download)

    with pytest.raises(ValueError, match="distincts"):
        enrich_commune.enrich_commune_sitadel_flow.fn(
            code_column=code_column, population_column=population_column
        )

    download.assert_not_called()


@pytest.fixture
def database(monkeypatch):
    """Isole les tests PostgreSQL dans un schéma temporaire dédié."""
    url = os.environ.get("SITADEL_TEST_DATABASE_URL")
    if not url:
        pytest.skip("SITADEL_TEST_DATABASE_URL non définie.")
    engine = create_engine(url)
    schema = f"test_sitadel_{uuid4().hex[:12]}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(
            text(
                f'CREATE TABLE "{schema}".commune ('
                "code_insee text PRIMARY KEY, population integer, name text);"
                f'INSERT INTO "{schema}".commune VALUES '
                "('01001', 2000, 'Commune conservée'),"
                "('2A004', 0, 'Population nulle'),"
                "('97411', NULL, 'Population inconnue'),"
                "('01002', -1, 'Population invalide'),"
                "('99999', 100, 'Sans correspondance');"
            )
        )
    monkeypatch.setattr(enrich_commune, "create_engine", lambda **kwargs: engine)
    try:
        yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_database_update_and_rerun(database, tmp_path):
    """Vérifie les taux, les NULL, la conservation des lignes et l'idempotence."""
    engine, schema = database
    rows = [
        row
        for code in ("01001", "2A004", "97411", "01002")
        for row in housing_rows(code)
    ]
    source = write_source(tmp_path, rows)
    for _ in range(2):
        enrich_commune.enrich_commune_sitadel_flow.fn(
            source_file=source, db_schema=schema, end_year=2025
        )
    with engine.connect() as connection:
        records = (
            connection.execute(
                text(f'SELECT * FROM "{schema}".commune ORDER BY code_insee')
            )
            .mappings()
            .all()
        )
        comments = connection.execute(
            text(
                "SELECT col_description(attrelid, attnum) FROM pg_attribute "
                "WHERE attrelid = CAST(:table_name AS regclass) "
                "AND attname = :column_name"
            ),
            {"table_name": f'"{schema}".commune', "column_name": "housing_created_10y"},
        ).scalar_one()
    assert len(records) == 5
    by_code = {row["code_insee"]: row for row in records}
    assert by_code["01001"]["name"] == "Commune conservée"
    assert by_code["01001"]["housing_created_10y"] == 100
    assert by_code["01001"]["collective_housing_created_10y"] == 30
    assert by_code["01001"]["individual_housing_created_10y"] == 30
    assert by_code["01001"][enrich_commune.RATE_COLUMN] == 50
    for code in ("2A004", "97411", "01002", "99999"):
        assert by_code[code][enrich_commune.RATE_COLUMN] is None
    assert by_code["99999"]["housing_created_10y"] is None
    assert "2016-2025" in comments

    rows = housing_rows("01001")
    rows[0]["LOG_COM"] = ""
    source = write_source(tmp_path, rows)
    enrich_commune.enrich_commune_sitadel_flow.fn(
        source_file=source, db_schema=schema, end_year=2025
    )
    with engine.connect() as connection:
        records = (
            connection.execute(text(f'SELECT * FROM "{schema}".commune'))
            .mappings()
            .all()
        )
    by_code = {row["code_insee"]: row for row in records}
    assert by_code["01001"]["housing_created_10y"] is None
    assert by_code["01001"][enrich_commune.RATE_COLUMN] is None
    assert by_code["01001"]["collective_housing_created_10y"] == 30
    assert by_code["2A004"]["housing_created_10y"] is None


def test_database_custom_identifiers(database, tmp_path):
    """Protège les noms personnalisés et calcule les taux sans division entière."""
    engine, schema = database
    with engine.begin() as connection:
        connection.execute(
            text(
                f'CREATE TABLE "{schema}"."Table commune" '
                '("Code INSEE" text, "Population totale" integer);'
                f'INSERT INTO "{schema}"."Table commune" VALUES (\'01001\', 3000)'
            )
        )
    source = write_source(tmp_path, housing_rows())

    enrich_commune.enrich_commune_sitadel_flow.fn(
        source_file=source,
        db_schema=schema,
        table_name="Table commune",
        code_column="Code INSEE",
        population_column="Population totale",
        end_year=2025,
    )
    with engine.connect() as connection:
        rate = connection.execute(
            text(f'SELECT {enrich_commune.RATE_COLUMN} FROM "{schema}"."Table commune"')
        ).scalar_one()
    assert float(rate) == pytest.approx(100 / 3)


@pytest.mark.parametrize("failure", ["no_match", "missing_column", "sql"])
def test_database_failure_rolls_back(database, tmp_path, failure):
    """N'ajoute aucune colonne et préserve la table lorsqu'une étape échoue."""
    engine, schema = database
    source = write_source(
        tmp_path, housing_rows("88888" if failure == "no_match" else "01001")
    )
    if failure == "sql":
        with engine.begin() as connection:
            connection.execute(
                text(
                    f'ALTER TABLE "{schema}".commune ALTER COLUMN population '
                    "TYPE text USING population::text"
                )
            )
    expected_error = ValueError
    if failure == "sql":
        from sqlalchemy.exc import ProgrammingError

        expected_error = ProgrammingError
    with pytest.raises(expected_error):
        enrich_commune.enrich_commune_sitadel_flow.fn(
            source_file=source,
            db_schema=schema,
            population_column="absente"
            if failure == "missing_column"
            else "population",
            end_year=2025,
        )
    with engine.connect() as connection:
        columns = inspect(connection).get_columns("commune", schema=schema)
        assert {column["name"] for column in columns} == {
            "code_insee",
            "population",
            "name",
        }
        assert (
            connection.execute(
                text(f'SELECT count(*) FROM "{schema}".commune')
            ).scalar_one()
            == 5
        )
