"""Tests de construction incrémentale de l'historique des parcelles."""

import os
import zipfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import duckdb
import geopandas as gpd
import pytest
import requests
from flows.cadastre.import_parcelles_historique import (
    CURRENT_VIEW,
    HISTORY_TABLE,
    IMPORT_LOG_TABLE,
    MILLESIME_FUNCTION,
    ParcelSource,
    build_source_location,
    import_departement_millesime,
    import_parcelles_historique_flow,
    is_not_found_error,
    list_available_millesimes,
    open_parcel_source,
    parse_departements,
    parse_millesimes,
    select_millesimes,
    source_format,
)
from shapely.geometry import Polygon
from sqlalchemy import create_engine, text

MODULE = "flows.cadastre.import_parcelles_historique"
DEPARTEMENT = "90"


def square(offset: int) -> Polygon:
    """Construit un carré de 10 m en Lambert-93, décalé selon l'index."""
    x, y = 990000 + offset * 20, 6730000
    return Polygon([(x, y), (x + 10, y), (x + 10, y + 10), (x, y + 10)])


def parcel_id(suffix: str) -> str:
    """Construit un identifiant de parcelle de la commune 90001."""
    return f"900010000A{suffix}"


def write_shapefile_millesime(base: Path, millesime: str, suffixes: list[str]) -> None:
    """Écrit l'archive shapefile départementale d'un millésime."""
    directory = base / millesime / "shp" / "departements" / DEPARTEMENT
    directory.mkdir(parents=True)
    frame = gpd.GeoDataFrame(
        {
            "id": [parcel_id(suffix) for suffix in suffixes],
            "commune": "90001",
            "prefixe": "000",
            "section": "A",
            "numero": suffixes,
            "contenance": [100.0] * len(suffixes),
            "created": [date(2004, 5, 24)] * len(suffixes),
            "updated": [date(2016, 10, 13)] * len(suffixes),
        },
        geometry=[square(int(suffix)) for suffix in suffixes],
        crs="EPSG:2154",
    )
    shapefile_dir = base / "shp_tmp" / millesime
    shapefile_dir.mkdir(parents=True)
    frame.to_file(shapefile_dir / "parcelles.shp")
    with zipfile.ZipFile(
        directory / f"cadastre-{DEPARTEMENT}-parcelles-shp.zip", "w"
    ) as archive:
        for path in shapefile_dir.iterdir():
            archive.write(path, path.name)


def write_geoparquet_millesime(base: Path, millesime: str, suffixes: list[str]) -> None:
    """Écrit le GeoParquet national d'un millésime, avec des objets à ignorer."""
    (base / millesime / "shp" / "departements" / DEPARTEMENT).mkdir(parents=True)
    directory = base / millesime / "geoparquet" / "france"
    directory.mkdir(parents=True)
    with duckdb.connect() as connection:
        connection.execute(
            """
            CREATE TABLE cadastre (
                millesime DATE, departement VARCHAR, commune VARCHAR,
                type_objet VARCHAR, id VARCHAR, prefixe VARCHAR, section VARCHAR,
                numero VARCHAR, contenance BIGINT, created DATE, updated DATE,
                geometry BLOB, geom_srid INTEGER
            )
            """
        )
        rows = [
            (departement, object_type, parcel_id(suffix), suffix)
            for suffix in suffixes
            for departement, object_type in (
                (DEPARTEMENT, "parcelles"),
                (DEPARTEMENT, "batiments"),
                ("35", "parcelles"),
            )
        ]
        for departement, object_type, identifier, suffix in rows:
            if departement == "35":
                identifier = identifier.replace("90001", "35001")
            connection.execute(
                "INSERT INTO cadastre VALUES (?, ?, ?, ?, ?, '000', 'A', ?, 100, "
                "DATE '2004-05-24', DATE '2024-06-12', ?, 2154)",
                [
                    millesime,
                    departement,
                    f"{departement}001",
                    object_type,
                    identifier,
                    suffix,
                    square(int(suffix)).wkb,
                ],
            )
        connection.execute(
            "COPY cadastre TO ? (FORMAT PARQUET)",
            [str(directory / "cadastre.parquet")],
        )


@pytest.fixture
def etalab_tree(tmp_path: Path) -> Path:
    """Reproduit localement l'arborescence etalab-cadastre sur trois millésimes."""
    base = tmp_path / "etalab-cadastre"
    base.mkdir()
    (base / "2018-01-02").mkdir()
    write_shapefile_millesime(base, "2024-10-01", ["0001", "0002"])
    write_geoparquet_millesime(base, "2025-04-01", ["0002", "0003"])
    return base


def test_select_millesimes_excludes_communal_and_old_millesimes():
    """Exclut les millésimes communaux et antérieurs au 3 avril 2018."""
    available = [
        date(2017, 7, 6),
        date(2017, 10, 12),
        date(2018, 1, 2),
        date(2018, 4, 3),
        date(2025, 4, 1),
    ]
    assert select_millesimes(available, None) == [date(2018, 4, 3), date(2025, 4, 1)]
    assert select_millesimes(available, [date(2025, 4, 1)]) == [date(2025, 4, 1)]
    with pytest.raises(ValueError, match="hors périmètre"):
        select_millesimes(available, [date(2018, 1, 2)])
    with pytest.raises(ValueError, match="non publiés"):
        select_millesimes(available, [date(2019, 1, 1)])


def test_source_format_and_location():
    """Utilise le GeoParquet à partir du 1er avril 2025, le shapefile avant."""
    assert source_format(date(2025, 1, 1)) == "shp"
    assert source_format(date(2025, 4, 1)) == "geoparquet"
    assert build_source_location("https://x/", date(2018, 4, 3), "2A") == (
        "https://x/2018-04-03/shp/departements/2A/cadastre-2A-parcelles-shp.zip"
    )
    assert build_source_location("https://x", date(2025, 9, 1), "35") == (
        "https://x/2025-09-01/geoparquet/france/cadastre.parquet"
    )


def test_parse_options():
    """Normalise les départements et refuse les valeurs mal formées."""
    assert parse_departements("1, 2a,974,35,35") == ["01", "2A", "974", "35"]
    assert parse_millesimes("2025-04-01,2024-10-01") == [
        date(2024, 10, 1),
        date(2025, 4, 1),
    ]
    with pytest.raises(ValueError, match="département"):
        parse_departements("35'; DROP TABLE x")
    with pytest.raises(ValueError, match="Millésimes invalides"):
        parse_millesimes("2025-13-01")


def test_list_remote_millesimes():
    """Lit les millésimes depuis l'index HTML de cadastre.data.gouv.fr."""
    response = MagicMock()
    response.text = (
        '<a href="../">..</a>'
        '<a href="/data/etalab-cadastre/2018-04-03/">2018-04-03/</a>'
        '<a href="/data/etalab-cadastre/2017-07-06/">2017-07-06/</a>'
    )
    with patch(f"{MODULE}.requests.get", return_value=response):
        assert list_available_millesimes("https://example.org/etalab-cadastre") == [
            date(2017, 7, 6),
            date(2018, 4, 3),
        ]


def test_is_not_found_error():
    """Reconnaît les 404 renvoyés par requests et par DuckDB (status_code)."""
    response = requests.Response()
    response.status_code = 404
    assert is_not_found_error(requests.HTTPError(response=response))
    response.status_code = 500
    assert not is_not_found_error(requests.HTTPError(response=response))
    duckdb_error = duckdb.HTTPException("HTTP 404")
    duckdb_error.status_code = 404
    assert is_not_found_error(duckdb_error)


@pytest.mark.parametrize("millesime", [date(2024, 10, 1), date(2025, 4, 1)])
def test_read_local_sources(etalab_tree, millesime):
    """Lit identifiants puis lignes sélectionnées en shapefile et GeoParquet."""
    with open_parcel_source(str(etalab_tree), millesime, DEPARTEMENT) as source:
        ids = source.read_ids()
        rows = list(source.iter_rows({parcel_id("0002")}))
    expected_suffixes = ["0001", "0002"] if millesime.year == 2024 else ["0002", "0003"]
    assert sorted(ids) == [parcel_id(suffix) for suffix in expected_suffixes]
    assert len(rows) == 1
    identifier, commune, prefixe, section, numero, contenance, created = rows[0][:7]
    assert (identifier, commune, prefixe, section, numero, contenance, created) == (
        parcel_id("0002"),
        "90001",
        "000",
        "A",
        "0002",
        100,
        date(2004, 5, 24),
    )
    assert isinstance(rows[0][-2], bytes)
    assert rows[0][-1] == 2154


def test_cli_routes_options(monkeypatch):
    """Vérifie le routage de la commande Typer vers le flow."""
    from cli.app import app
    from typer.testing import CliRunner

    monkeypatch.setenv("IMPORT_SCHEMA", "cadastre_test")
    with patch(
        "cli.commands.cadastre.import_parcelles_historique_flow"
    ) as history_flow:
        result = CliRunner().invoke(
            app,
            [
                "parcelles-historique",
                "-d",
                "35,22",
                "-m",
                "2025-04-01",
                "--source",
                "/data/etalab",
            ],
        )
    assert result.exit_code == 0, result.output
    history_flow.assert_called_once_with(
        departements="35,22",
        millesimes="2025-04-01",
        db_schema="cadastre_test",
        base_location="/data/etalab",
    )


@pytest.fixture
def database():
    """Isole les tests PostGIS dans un schéma supprimé après chaque test."""
    url = os.environ.get("DGFIP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("DGFIP_TEST_DATABASE_URL non définie pour les tests PostGIS.")
    engine = create_engine(url)
    schema = f"test_parcelles_{uuid4().hex[:12]}"
    try:
        yield engine, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def read_history(engine, schema: str) -> list[tuple]:
    """Renvoie l'historique sous forme (id, début, fin), trié."""
    with engine.connect() as connection:
        return connection.execute(
            text(
                f'SELECT id, millesime_debut, millesime_fin FROM "{schema}".'
                f"{HISTORY_TABLE} ORDER BY id, millesime_debut"
            )
        ).fetchall()


def test_postgis_incremental_history(etalab_tree, database):
    """Vérifie insertions, clôtures, réapparition, filtres et idempotence."""
    engine, schema = database
    with patch(f"{MODULE}.create_engine", return_value=engine):
        results = import_parcelles_historique_flow.fn(
            db_schema=schema, base_location=str(etalab_tree)
        )
        assert [
            (result["millesime"], result["nb_nouvelles"], result["nb_disparues"])
            for result in results
        ] == [(date(2024, 10, 1), 2, 0), (date(2025, 4, 1), 1, 1)]
        assert read_history(engine, schema) == [
            (parcel_id("0001"), date(2024, 10, 1), date(2025, 4, 1)),
            (parcel_id("0002"), date(2024, 10, 1), None),
            (parcel_id("0003"), date(2025, 4, 1), None),
        ]
        # Relance sans nouveau millésime : aucun import.
        assert (
            import_parcelles_historique_flow.fn(
                db_schema=schema, base_location=str(etalab_tree)
            )
            == []
        )
        # Nouveau millésime : 0001 réapparaît, 0002 disparaît.
        write_geoparquet_millesime(etalab_tree, "2025-09-01", ["0001", "0003"])
        results = import_parcelles_historique_flow.fn(
            departements=DEPARTEMENT, db_schema=schema, base_location=str(etalab_tree)
        )
        assert [(r["nb_nouvelles"], r["nb_disparues"]) for r in results] == [(1, 1)]
    assert read_history(engine, schema) == [
        (parcel_id("0001"), date(2024, 10, 1), date(2025, 4, 1)),
        (parcel_id("0001"), date(2025, 9, 1), None),
        (parcel_id("0002"), date(2024, 10, 1), date(2025, 9, 1)),
        (parcel_id("0003"), date(2025, 4, 1), None),
    ]
    with engine.connect() as connection:

        def ids_at(millesime: str) -> list[str]:
            """Renvoie les parcelles existantes à un millésime via la fonction."""
            return connection.scalars(
                text(
                    f'SELECT id FROM "{schema}".{MILLESIME_FUNCTION}(:millesime) '
                    "ORDER BY id"
                ),
                {"millesime": millesime},
            ).all()

        assert ids_at("2024-10-01") == [parcel_id("0001"), parcel_id("0002")]
        assert ids_at("2025-04-01") == [parcel_id("0002"), parcel_id("0003")]
        assert ids_at("2025-06-15") == [parcel_id("0002"), parcel_id("0003")]
        assert ids_at("2025-09-01") == [parcel_id("0001"), parcel_id("0003")]
        assert ids_at("2020-01-01") == []
        assert connection.scalars(
            text(f'SELECT id FROM "{schema}".{CURRENT_VIEW} ORDER BY id')
        ).all() == [parcel_id("0001"), parcel_id("0003")]
        assert connection.execute(
            text(
                f"SELECT DISTINCT ST_SRID(geom), ST_GeometryType(geom), departement, "
                f'commune, contenance FROM "{schema}".{HISTORY_TABLE}'
            )
        ).fetchall() == [(2154, "ST_MultiPolygon", DEPARTEMENT, "90001", 100)]
        assert connection.execute(
            text(
                "SELECT millesime, format, nb_parcelles, nb_nouvelles, nb_disparues "
                f'FROM "{schema}".{IMPORT_LOG_TABLE} ORDER BY millesime'
            )
        ).fetchall() == [
            (date(2024, 10, 1), "shp", 2, 2, 0),
            (date(2025, 4, 1), "geoparquet", 2, 1, 1),
            (date(2025, 9, 1), "geoparquet", 2, 1, 1),
        ]


def test_postgis_rollback_and_older_millesime(etalab_tree, database):
    """Annule un import en erreur et refuse un millésime antérieur au dernier."""
    engine, schema = database

    @contextmanager
    def failing_source(*_):
        """Source dont la lecture des géométries échoue en cours d'import."""

        def iter_rows(_ids):
            raise RuntimeError("Lecture interrompue")
            yield

        yield ParcelSource(lambda: [parcel_id("0009")], iter_rows)

    with patch(f"{MODULE}.create_engine", return_value=engine):
        import_parcelles_historique_flow.fn(
            millesimes="2025-04-01", db_schema=schema, base_location=str(etalab_tree)
        )
        with pytest.raises(RuntimeError, match="Lecture interrompue"):
            import_departement_millesime(
                engine,
                schema,
                str(etalab_tree),
                DEPARTEMENT,
                date(2025, 9, 1),
                open_source=failing_source,
            )
        assert read_history(engine, schema) == [
            (parcel_id("0002"), date(2025, 4, 1), None),
            (parcel_id("0003"), date(2025, 4, 1), None),
        ]
        assert (
            import_parcelles_historique_flow.fn(
                millesimes="2024-10-01",
                db_schema=schema,
                base_location=str(etalab_tree),
            )
            == []
        )
    assert len(read_history(engine, schema)) == 2


def test_postgis_refuses_concurrent_flow(etalab_tree, database):
    """Refuse un second flow tant qu'un import est en cours sur le schéma."""
    engine, schema = database
    with engine.connect() as connection:
        connection.execute(
            text("SELECT pg_advisory_lock(hashtext(:lock_name))"),
            {"lock_name": f"{schema}.{HISTORY_TABLE}.flow"},
        )
        with (
            patch(f"{MODULE}.create_engine", return_value=engine),
            pytest.raises(RuntimeError, match="Un autre import"),
        ):
            import_parcelles_historique_flow.fn(
                db_schema=schema, base_location=str(etalab_tree)
            )
        connection.execute(
            text("SELECT pg_advisory_unlock(hashtext(:lock_name))"),
            {"lock_name": f"{schema}.{HISTORY_TABLE}.flow"},
        )
