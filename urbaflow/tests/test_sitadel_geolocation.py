"""Tests de géolocalisation SITADEL sur les parcelles historiques."""

import csv
import json
import os
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from cli.app import app
from cli.commands import sitadel as sitadel_command
from flows.cadastre.import_parcelles_historique import ensure_history_tables
from flows.sitadel import geolocate_sitadel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from typer.testing import CliRunner


def authorization(identifier="PC1", **changes):
    """Construit une autorisation avec les 25 couples cadastraux SDES."""
    row = {
        "NUM_DAU": identifier,
        "COMM": "90001",
        "DATE_REELLE_AUTORISATION": "2019-01-01",
        "LIBELLE": "Donnée source conservée",
        **{
            f"{prefix}{index}": ""
            for index in range(1, 26)
            for prefix in ("SEC_CADASTRE", "NUM_CADASTRE")
        },
    }
    row.update(SEC_CADASTRE1="A", NUM_CADASTRE1="1")
    row.update(changes)
    return row


def write_source(tmp_path, rows, filename="sitadel_detail_logements.csv"):
    """Écrit un CSV SDES avec BOM et séparateur point-virgule."""
    source = tmp_path / filename
    with source.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    return source


@pytest.mark.parametrize("identifier_column", ["NUM_DAU", "NUM_PA", "NUM_PD"])
@pytest.mark.parametrize("commune", ["90001", "2A004", "97411"])
def test_read_all_detail_types_and_references(tmp_path, identifier_column, commune):
    """Préserve les données, les codes et les références jusqu'à la vingt-cinquième."""
    row = authorization(
        COMM=commune,
        SEC_CADASTRE2="0a",
        NUM_CADASTRE2="0001",
        SEC_CADASTRE25=" ab ",
        NUM_CADASTRE25=" 42 ",
    )
    row[identifier_column] = row.pop("NUM_DAU")
    [record] = list(
        geolocate_sitadel.iter_authorizations(write_source(tmp_path, [row]))
    )
    assert record["authorization_id"] == "PC1"
    assert record["authorization_date"] == date(2019, 1, 1)
    assert record["commune"] == commune
    assert record["source_line"] == 2
    assert json.loads(record["source_data"]) == row
    assert json.loads(record["parcel_references"]) == [
        {"section": "0A", "numero": "0001"},
        {"section": "AB", "numero": "0042"},
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("COMM", "1001"),
        ("SEC_CADASTRE1", "000AB"),
        ("SEC_CADASTRE1", ""),
        ("NUM_CADASTRE1", "1,2"),
        ("NUM_CADASTRE1", "0"),
        ("NUM_CADASTRE1", "-1"),
        ("NUM_CADASTRE1", "12345"),
    ],
)
def test_unknown_reference_is_retained(tmp_path, field, value):
    """Conserve une référence incorrecte pour le diagnostic, sans la deviner."""
    row = authorization(**{field: value})
    [record] = list(
        geolocate_sitadel.iter_authorizations(write_source(tmp_path, [row]))
    )
    assert json.loads(record["parcel_references"]) == [
        {"section": None, "numero": None}
    ]
    assert json.loads(record["source_data"])[field] == value


def test_missing_date_and_reference(tmp_path):
    """Laisse la date inconnue et la liste des références vide, sans valeur fictive."""
    row = authorization(DATE_REELLE_AUTORISATION="", SEC_CADASTRE1="", NUM_CADASTRE1="")
    [record] = list(
        geolocate_sitadel.iter_authorizations(write_source(tmp_path, [row]))
    )
    assert record["authorization_date"] is None
    assert json.loads(record["parcel_references"]) == []


@pytest.mark.parametrize(
    "problem", ["header", "unpaired", "duplicate_header", "date", "id", "shape"]
)
def test_invalid_csv_fails_explicitly(tmp_path, problem):
    """Refuse les en-têtes, dates et lignes mal formés."""
    row = authorization()
    if problem == "header":
        del row["COMM"]
    elif problem == "unpaired":
        del row["NUM_CADASTRE25"]
    elif problem == "date":
        row["DATE_REELLE_AUTORISATION"] = "2019-13-40"
    elif problem == "id":
        row["NUM_DAU"] = ""
    source = write_source(tmp_path, [row])
    if problem == "duplicate_header":
        source.write_text("COMM;COMM\n90001;90001\n", encoding="utf-8")
    elif problem == "shape":
        with source.open("a", encoding="utf-8") as output_file:
            output_file.write("ligne;tronquée\n")
    with pytest.raises(ValueError):
        list(geolocate_sitadel.iter_authorizations(source))


def test_staging_uses_batches(monkeypatch, tmp_path):
    """Charge les données par lots bornés, y compris le dernier lot incomplet."""
    monkeypatch.setattr(geolocate_sitadel, "BATCH_SIZE", 2)
    connection = MagicMock()
    source = write_source(tmp_path, [authorization(str(index)) for index in range(5)])
    assert geolocate_sitadel.stage_authorizations(connection, source) == 5
    assert [len(call.args[1]) for call in connection.execute.call_args_list] == [
        2,
        2,
        1,
    ]


def test_empty_source_rejected(tmp_path):
    """Un export vide ne doit pas effacer un résultat déjà publié."""
    source = write_source(tmp_path, [authorization()])
    header = source.read_text(encoding="utf-8-sig").splitlines()[0]
    source.write_text(header + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="vide"):
        geolocate_sitadel.stage_authorizations(MagicMock(), source)


@pytest.mark.parametrize("local_source", [False, True])
def test_flow_source_selection(monkeypatch, tmp_path, local_source):
    """Télécharge seulement les quatre exports détaillés, sauf avec un CSV local."""
    download = MagicMock(side_effect=lambda filename, directory: directory / filename)
    monkeypatch.setattr(geolocate_sitadel, "download_sitadel_file", download)
    monkeypatch.setattr(geolocate_sitadel, "TEMP_DIR", tmp_path)
    monkeypatch.setattr(
        geolocate_sitadel,
        "create_engine",
        MagicMock(side_effect=RuntimeError("Arrêt avant connexion")),
    )
    with pytest.raises(RuntimeError, match="Arrêt avant connexion"):
        geolocate_sitadel.geolocate_sitadel_flow.fn(
            source_file=tmp_path / "source.csv" if local_source else None
        )
    expected = [] if local_source else list(geolocate_sitadel.DETAIL_FILENAMES)
    assert [call.args[0] for call in download.call_args_list] == expected


def test_cannot_replace_history(monkeypatch):
    """Interdit de remplacer la source cadastrale par le résultat."""
    download = MagicMock()
    monkeypatch.setattr(geolocate_sitadel, "download_sitadel_file", download)
    with pytest.raises(ValueError, match="distincte"):
        geolocate_sitadel.geolocate_sitadel_flow.fn(
            table_name=geolocate_sitadel.HISTORY_TABLE
        )
    download.assert_not_called()


@pytest.mark.parametrize("explicit", [False, True])
def test_cli(monkeypatch, tmp_path, explicit):
    """Transmet les paramètres de la commande au flow."""
    run_flow = MagicMock()
    monkeypatch.setattr(sitadel_command, "geolocate_sitadel_flow", run_flow)
    arguments = ["sitadel-geolocate"]
    source = write_source(tmp_path, [authorization()])
    if explicit:
        arguments += [
            str(source),
            "--schema",
            "resultats",
            "--parcels-schema",
            "cadastre",
            "--table-name",
            "autorisations",
        ]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 0, result.output
    kwargs = run_flow.call_args.kwargs
    assert kwargs["source_file"] == (source if explicit else None)
    assert kwargs["parcels_schema"] == ("cadastre" if explicit else None)
    assert kwargs["table_name"] == (
        "autorisations" if explicit else "sitadel_geolocalisation"
    )
    if explicit:
        assert kwargs["db_schema"] == "resultats"


@pytest.mark.parametrize("source_type", ["missing", "directory"])
def test_cli_rejects_invalid_path(monkeypatch, tmp_path, source_type):
    """Refuse un chemin absent ou un répertoire avant de lancer le flow."""
    run_flow = MagicMock()
    monkeypatch.setattr(sitadel_command, "geolocate_sitadel_flow", run_flow)
    source = tmp_path / "source"
    if source_type == "directory":
        source.mkdir()
    result = CliRunner().invoke(app, ["sitadel-geolocate", str(source)])
    assert result.exit_code == 2
    run_flow.assert_not_called()


@pytest.fixture
def database(monkeypatch):
    """Crée un historique PostGIS isolé, puis supprime uniquement son schéma."""
    url = os.environ.get("DGFIP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("DGFIP_TEST_DATABASE_URL non définie pour les tests PostGIS.")
    engine = create_engine(url)
    schema = f"test_sitadel_geo_{uuid4().hex[:12]}"
    with engine.begin() as connection:
        ensure_history_tables(connection, schema)
        parcels = [
            ("90001", "000", "A", "1", "2018-04-03", "2020-01-01", 0),
            ("90001", "000", "A", "1", "2022-01-01", None, 200),
            ("90001", "000", "A", "2", "2018-04-03", None, 20),
            ("90001", "000", "B", "1", "2018-04-03", None, 40),
            ("90001", "001", "B", "1", "2018-04-03", None, 60),
            ("90001", "000", "C", "1", "2018-04-03", "2020-01-01", 80),
            ("90001", "001", "C", "1", "2020-01-11", None, 100),
            ("2A004", "000", "AB", "42", "2018-04-03", None, 120),
            ("97411", "000", "A", "1", "2018-04-03", None, 140),
        ]
        for commune, prefix, section, number, start, end, offset in parcels:
            identifier = commune + prefix + section.zfill(2) + number.zfill(4)
            connection.execute(
                text(
                    f'INSERT INTO "{schema}".dgfip_parcelle_historique '
                    "(id, departement, commune, prefixe, section, numero, geom_srid, "
                    "millesime_debut, millesime_fin, geom) VALUES "
                    "(:id, :departement, :commune, :prefix, :section, :number, 2154, "
                    ":start, :end, ST_Multi(ST_MakeEnvelope("
                    ":x, 6730000, :x + 10, 6730010, 2154)))"
                ),
                {
                    "id": identifier,
                    "departement": commune[:2],
                    "commune": commune,
                    "prefix": prefix,
                    "section": section,
                    "number": number,
                    "start": date.fromisoformat(start),
                    "end": date.fromisoformat(end) if end else None,
                    "x": 990000 + offset,
                },
            )
    monkeypatch.setattr(geolocate_sitadel, "create_engine", lambda **kwargs: engine)
    try:
        yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def read_results(engine, schema, table="sitadel_geolocalisation"):
    """Renvoie les résultats et les contrôles spatiaux par identifiant SITADEL."""
    quoted_table = geolocate_sitadel.quote_identifier(table)
    with engine.connect() as connection:
        records = (
            connection.execute(
                text(
                    f"SELECT *, ST_XMin(geom) AS xmin, ST_Area(geom) AS area, "
                    "ST_SRID(geom) AS srid, ST_Covers(geom, location) AS covers, "
                    "ST_Equals(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), "
                    "ST_Transform(location, 4326)) AS coordinates_match, "
                    "ST_GeometryType(geom) AS geometry_type "
                    f'FROM "{schema}".{quoted_table} ORDER BY source_line'
                )
            )
            .mappings()
            .all()
        )
    return {row["authorization_id"]: row for row in records}


def test_postgis_temporal_matching_geometry_and_diagnostics(database, tmp_path):
    """Vérifie versions disparues, bornes, replis, ambiguïtés et géométries réelles."""
    engine, schema = database
    rows = [
        authorization("ancien"),
        authorization("reapparu", DATE_REELLE_AUTORISATION="2023-01-01"),
        authorization("avant_historique", DATE_REELLE_AUTORISATION="2013-01-01"),
        authorization("sans_date", DATE_REELLE_AUTORISATION=""),
        authorization("ambigu", SEC_CADASTRE1="B"),
        authorization("introuvable", NUM_CADASTRE1="999"),
        authorization("invalide", NUM_CADASTRE1="nd"),
        authorization("sans_reference", SEC_CADASTRE1="", NUM_CADASTRE1=""),
        authorization("partiel", SEC_CADASTRE2="A", NUM_CADASTRE2="999"),
        authorization("multiple", SEC_CADASTRE25="A", NUM_CADASTRE25="2"),
        authorization(
            "egalite_hors_periode",
            SEC_CADASTRE1="C",
            DATE_REELLE_AUTORISATION="2020-01-06",
        ),
        authorization(
            "borne_debut",
            SEC_CADASTRE1="C",
            DATE_REELLE_AUTORISATION="2020-01-11",
        ),
        authorization(
            "borne_fin",
            SEC_CADASTRE1="C",
            DATE_REELLE_AUTORISATION="2020-01-01",
        ),
        authorization("corse", COMM="2A004", SEC_CADASTRE1="AB", NUM_CADASTRE1="42"),
        authorization("outre_mer", COMM="97411"),
    ]
    source = write_source(tmp_path, rows)
    statuses = geolocate_sitadel.geolocate_sitadel_flow.fn(
        source_file=source, db_schema=schema
    )
    assert statuses == {
        "complet": 8,
        "partiel": 1,
        "non_geolocalise": 5,
        "sans_reference": 1,
    }
    records = read_results(engine, schema)
    assert len(records) == len(rows)
    assert records["ancien"]["xmin"] == 990000
    assert records["reapparu"]["xmin"] == 990200
    assert records["avant_historique"]["xmin"] == 990000
    assert records["borne_debut"]["xmin"] == 990100
    assert records["borne_fin"]["xmin"] == 990080
    expected_methods = {
        "ancien": "periode",
        "reapparu": "periode",
        "avant_historique": "plus_proche",
        "sans_date": "date_absente",
        "ambigu": "ambigu",
        "introuvable": "introuvable",
        "invalide": "reference_invalide",
        "egalite_hors_periode": "ambigu",
        "borne_debut": "periode",
        "borne_fin": "plus_proche",
    }
    for identifier, method in expected_methods.items():
        assert records[identifier]["parcel_matches"][0]["method"] == method
    for record in records.values():
        assert record["source_data"]["NUM_DAU"] == record["authorization_id"]
        if record["matched_count"]:
            assert record["srid"] == 2154
            assert record["geometry_type"] == "ST_MultiPolygon"
            assert record["covers"] is True
            assert record["coordinates_match"] is True
            assert -180 <= record["longitude"] <= 180
            assert -90 <= record["latitude"] <= 90
        else:
            assert record["geom"] is None
            assert record["location"] is None
            assert record["longitude"] is None
            assert record["latitude"] is None
    assert records["multiple"]["area"] == 200
    assert records["multiple"]["reference_count"] == 2
    assert records["multiple"]["matched_count"] == 2
    assert records["partiel"]["reference_count"] == 2
    assert records["partiel"]["matched_count"] == 1
    assert records["partiel"]["area"] == 100
    assert records["sans_reference"]["parcel_matches"] == []


def test_postgis_rerun_replaces_only_imported_file(database, tmp_path):
    """Actualise les coordonnées sans modifier les résultats des autres CSV."""
    engine, schema = database
    source = write_source(tmp_path, [authorization("PC1"), authorization("PC2")])
    other_source = write_source(
        tmp_path, [authorization("PD1")], filename="sitadel_detail_permis_demolir.csv"
    )
    for path in (source, other_source, source):
        geolocate_sitadel.geolocate_sitadel_flow.fn(source_file=path, db_schema=schema)
    assert len(read_results(engine, schema)) == 3
    source = write_source(tmp_path, [authorization("PC1", NUM_CADASTRE1="999")])
    geolocate_sitadel.geolocate_sitadel_flow.fn(source_file=source, db_schema=schema)
    records = read_results(engine, schema)
    assert set(records) == {"PC1", "PD1"}
    assert records["PC1"]["geom"] is None
    assert records["PD1"]["matched_count"] == 1


def test_postgis_transaction_rollback(database, tmp_path):
    """Ne publie aucune modification si un CSV est invalide ou si le SQL échoue."""
    engine, schema = database
    source = write_source(tmp_path, [authorization()])
    geolocate_sitadel.geolocate_sitadel_flow.fn(source_file=source, db_schema=schema)
    source = write_source(
        tmp_path, [authorization(), authorization("PC2", DATE_REELLE_AUTORISATION="nd")]
    )
    with pytest.raises(ValueError, match="Date"):
        geolocate_sitadel.geolocate_sitadel_flow.fn(
            source_file=source, db_schema=schema
        )
    assert set(read_results(engine, schema)) == {"PC1"}
    with engine.begin() as connection:
        connection.execute(
            text(
                f'ALTER TABLE "{schema}".sitadel_geolocalisation '
                "ADD CONSTRAINT no_new_id CHECK (authorization_id = 'PC1')"
            )
        )
    source = write_source(tmp_path, [authorization("PC2")])
    with pytest.raises(IntegrityError):
        geolocate_sitadel.geolocate_sitadel_flow.fn(
            source_file=source, db_schema=schema
        )
    assert set(read_results(engine, schema)) == {"PC1"}


def test_postgis_custom_table_and_separate_schema(database, tmp_path):
    """Protège les identifiants personnalisés et lit un historique d'un autre schéma."""
    engine, schema = database
    target_schema = f"{schema}_output"
    table = 'résultats "SITADEL"'
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{target_schema}"'))
    try:
        source = write_source(tmp_path, [authorization()])
        geolocate_sitadel.geolocate_sitadel_flow.fn(
            source_file=source,
            db_schema=target_schema,
            parcels_schema=schema,
            table_name=table,
        )
        assert read_results(engine, target_schema, table)["PC1"]["matched_count"] == 1
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{target_schema}" CASCADE'))


def test_postgis_default_four_exports(database, tmp_path, monkeypatch):
    """Conserve les autorisations communes aux exports, sans les dédoubler entre CSV."""
    engine, schema = database
    sources = {}
    for filename in geolocate_sitadel.DETAIL_FILENAMES:
        row = authorization()
        if "amenager" in filename:
            row["NUM_PA"] = row.pop("NUM_DAU")
        elif "demolir" in filename:
            row["NUM_PD"] = row.pop("NUM_DAU")
        sources[filename] = write_source(tmp_path, [row], filename)
    monkeypatch.setattr(
        geolocate_sitadel,
        "download_sitadel_file",
        lambda filename, directory: sources[filename],
    )
    for _ in range(2):
        assert geolocate_sitadel.geolocate_sitadel_flow.fn(db_schema=schema) == {
            "complet": 4
        }
    with engine.connect() as connection:
        files = (
            connection.execute(
                text(f'SELECT source_file FROM "{schema}".sitadel_geolocalisation')
            )
            .scalars()
            .all()
        )
    assert set(files) == set(geolocate_sitadel.DETAIL_FILENAMES)


def test_postgis_missing_history_preserves_results(database, tmp_path):
    """Un historique absent ne doit pas effacer les résultats précédents."""
    engine, schema = database
    source = write_source(tmp_path, [authorization()])
    geolocate_sitadel.geolocate_sitadel_flow.fn(source_file=source, db_schema=schema)
    with engine.begin() as connection:
        connection.execute(
            text(
                f'ALTER TABLE "{schema}".dgfip_parcelle_historique '
                "RENAME TO historique_indisponible"
            )
        )
    with pytest.raises(ProgrammingError):
        geolocate_sitadel.geolocate_sitadel_flow.fn(
            source_file=source, db_schema=schema
        )
    assert set(read_results(engine, schema)) == {"PC1"}
