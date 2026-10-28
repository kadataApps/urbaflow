from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from flows.bdtopo import import_bdtopo_troncon_route as route_import
from shared_tasks.geopf_utils import GeopfResource
from sqlalchemy.dialects.postgresql import dialect
from typer.testing import CliRunner

RESOURCE = GeopfResource("BDTOPO_TEST", "2026-06-15", "https://example.org/test.7z")
COLUMNS = [
    "fid",
    "cleabs",
    "nature",
    "insee_commune_gauche",
    "insee_commune_droite",
    "geom",
]


@pytest.mark.parametrize(
    ("provided", "expected"),
    [("1", "01"), (" 35 ", "35"), ("2a", "2A"), ("2B", "2B"), ("974", "974")],
)
def test_validate_department(provided: str, expected: str) -> None:
    """Vérifie la normalisation des départements métropolitains et ultramarins."""
    assert route_import.validate_department(provided) == expected


@pytest.mark.parametrize(
    "provided", ["", "00", "20", "96", "975", "99", "35,22", "35000", "35' OR 1=1"]
)
def test_validate_department_rejects_invalid_codes(provided: str) -> None:
    """Refuse les codes incorrects avant toute opération distante."""
    with pytest.raises(ValueError):
        route_import.validate_department(provided)


@pytest.mark.parametrize("department", ["35", "2A", "974"])
def test_department_filter_includes_both_sides(department: str) -> None:
    """Inclut les routes limitrophes sans imposer deux communes du département."""
    assert route_import.build_department_filter(department) == (
        f"(insee_commune_gauche LIKE '{department}%' "
        f"OR insee_commune_droite LIKE '{department}%')"
    )


def test_load_route_staging(monkeypatch, tmp_path: Path) -> None:
    """Vérifie le filtrage, la reprojection implicite et l'aplatissement 2D."""
    import_layer = MagicMock()
    monkeypatch.setattr(route_import, "import_vector_layer", import_layer)
    geopackage = tmp_path / "source.gpkg"
    route_import.load_route_staging.fn(geopackage, "35", "public", "staging")
    import_layer.assert_called_once_with(
        file=str(geopackage),
        layer="troncon_de_route",
        table="staging",
        schema="public",
        replace=True,
        force_2d=True,
        where=route_import.build_department_filter("35"),
    )


def test_download_extracts_only_geopackage(monkeypatch, tmp_path: Path) -> None:
    """Vérifie le téléchargement en streaming et l'extraction ciblée."""
    download = MagicMock()
    extract = MagicMock(return_value=[tmp_path / "source.gpkg"])
    monkeypatch.setattr(route_import, "download_file", download)
    monkeypatch.setattr(route_import, "extract_7z_members", extract)
    assert route_import.download_route_geopackage.fn(RESOURCE, tmp_path) == (
        tmp_path / "source.gpkg"
    )
    download.assert_called_once_with(
        url=RESOURCE.download_url, target_path=tmp_path / "BDTOPO_TEST.7z"
    )
    assert extract.call_args.kwargs["members_regex"] == r"\.gpkg$"


@pytest.mark.parametrize("files", [[], [Path("a.gpkg"), Path("b.gpkg")]])
def test_download_requires_one_geopackage(monkeypatch, tmp_path, files) -> None:
    """Refuse une archive absente ou ambiguë au lieu de choisir arbitrairement."""
    monkeypatch.setattr(route_import, "download_file", MagicMock())
    monkeypatch.setattr(
        route_import, "extract_7z_members", MagicMock(return_value=files)
    )
    with pytest.raises(ValueError, match="exactement un GeoPackage"):
        route_import.download_route_geopackage.fn(RESOURCE, tmp_path)


@pytest.fixture
def database(monkeypatch):
    """Simule une connexion transactionnelle avec le quoting PostgreSQL réel."""
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.engine.dialect = dialect()
    columns_result = MagicMock()
    columns_result.scalars.return_value = COLUMNS
    count_result = MagicMock()
    count_result.scalar_one.return_value = 3
    insert_result = MagicMock(rowcount=3)
    connection.execute.side_effect = [
        columns_result,
        count_result,
        None,
        None,
        insert_result,
    ]
    monkeypatch.setattr(route_import, "create_engine", MagicMock(return_value=engine))
    return engine, connection


def test_replace_department_is_transactional(database) -> None:
    """Vérifie les attributs natifs, le millésime et la suppression ciblée."""
    engine, connection = database
    inserted = route_import.replace_department_routes.fn(
        "35", RESOURCE.edition_date, "schema-test", "routes", "staging"
    )
    assert inserted == 3
    calls = connection.execute.call_args_list
    creation = str(calls[2].args[0])
    assert 'LIKE "schema-test".staging' in creation
    assert "PRIMARY KEY (code_departement, cleabs)" in creation
    assert "USING GIST (geom)" in creation
    assert str(calls[3].args[0]) == (
        'DELETE FROM "schema-test".routes WHERE code_departement = :department'
    )
    assert calls[3].args[1] == {"department": "35"}
    insertion = str(calls[4].args[0])
    assert ", ".join(COLUMNS) in insertion
    assert calls[4].args[1] == {"department": "35", "edition": date(2026, 6, 15)}
    engine.begin.assert_called_once_with()
    engine.begin.return_value.__exit__.assert_called_once_with(None, None, None)
    engine.dispose.assert_called_once_with()


def test_empty_delivery_does_not_delete_routes(database) -> None:
    """Une livraison vide échoue avant de modifier la table cible."""
    engine, connection = database
    columns_result = MagicMock()
    columns_result.scalars.return_value = COLUMNS
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    connection.execute.side_effect = [columns_result, count_result]
    with pytest.raises(ValueError, match="Aucun tronçon"):
        route_import.replace_department_routes.fn(
            "35", RESOURCE.edition_date, "public", "routes", "staging"
        )
    assert connection.execute.call_count == 2
    assert engine.begin.return_value.__exit__.call_args.args[0] is ValueError
    engine.dispose.assert_called_once_with()


def test_incomplete_delivery_does_not_delete_routes(database) -> None:
    """Des champs obligatoires absents interrompent l'import avant suppression."""
    _, connection = database
    columns_result = MagicMock()
    columns_result.scalars.return_value = ["cleabs", "geom"]
    connection.execute.side_effect = [columns_result]
    with pytest.raises(ValueError, match="Champs BD TOPO obligatoires absents"):
        route_import.replace_department_routes.fn(
            "35", RESOURCE.edition_date, "public", "routes", "staging"
        )
    assert connection.execute.call_count == 1


def test_insert_error_rolls_back_department_deletion(database) -> None:
    """Une erreur après suppression provoque le rollback de la transaction."""
    engine, connection = database
    columns_result = MagicMock()
    columns_result.scalars.return_value = COLUMNS
    count_result = MagicMock()
    count_result.scalar_one.return_value = 3
    error = RuntimeError("Échec SQL de test")
    connection.execute.side_effect = [columns_result, count_result, None, None, error]
    with pytest.raises(RuntimeError, match="Échec SQL de test"):
        route_import.replace_department_routes.fn(
            "35", RESOURCE.edition_date, "public", "routes", "staging"
        )
    transaction_exit = engine.begin.return_value.__exit__.call_args
    assert transaction_exit.args[0] is RuntimeError
    assert transaction_exit.args[1] is error
    engine.dispose.assert_called_once_with()


@pytest.mark.parametrize("keep_files", [False, True])
@pytest.mark.parametrize("failed_step", [None, "download", "load", "replace"])
def test_flow_cleanup(monkeypatch, tmp_path, keep_files, failed_step) -> None:
    """Nettoie les ressources propres au flux, y compris après un échec."""
    monkeypatch.setattr(route_import, "DOWNLOAD_DIR", tmp_path)
    find = MagicMock(return_value=RESOURCE)
    download = MagicMock(return_value=tmp_path / "source.gpkg")
    load = MagicMock()
    replace = MagicMock(return_value=3)
    drop = MagicMock()
    steps = {"download": download, "load": load, "replace": replace}
    if failed_step:
        steps[failed_step].side_effect = RuntimeError("Échec de test")
    monkeypatch.setattr(route_import, "find_geopf_resource", find)
    monkeypatch.setattr(route_import, "download_route_geopackage", download)
    monkeypatch.setattr(route_import, "load_route_staging", load)
    monkeypatch.setattr(route_import, "replace_department_routes", replace)
    monkeypatch.setattr(route_import, "drop_route_staging", drop)

    def run_flow() -> None:
        """Exécute le corps du flux sans serveur Prefect."""
        route_import.import_bdtopo_troncon_route_flow.fn(
            department="1", keep_files=keep_files
        )

    if failed_step:
        with pytest.raises(RuntimeError, match="Échec de test"):
            run_flow()
    else:
        run_flow()
    find.assert_called_once_with(
        resource_id="BDTOPO",
        zone="D001",
        archive_format="GPKG",
        edition_date=None,
        exclude_name_substring="_DIFF",
    )
    directory = download.call_args.args[1]
    assert directory.exists() == keep_files
    if failed_step == "download":
        drop.assert_not_called()
    else:
        drop.assert_called_once()
        assert drop.call_args.args == ("public", load.call_args.args[3])
    if not failed_step:
        assert replace.call_args.kwargs["department"] == "01"
        assert replace.call_args.kwargs["edition_date"] == RESOURCE.edition_date


def test_cli_forwards_options(monkeypatch) -> None:
    """Vérifie la commande documentée et toutes ses options."""
    from cli.app import app
    from cli.commands import bdtopo

    run_flow = MagicMock()
    monkeypatch.setattr(bdtopo, "import_bdtopo_troncon_route_flow", run_flow)
    result = CliRunner().invoke(
        app,
        [
            "bdtopo-troncon-route",
            "-d",
            "2A",
            "--millesime",
            "2026-06-15",
            "--schema",
            "ign",
            "--table-name",
            "routes",
            "--keep-files",
        ],
    )
    assert result.exit_code == 0, result.output
    run_flow.assert_called_once_with(
        department="2A",
        edition_date="2026-06-15",
        db_schema="ign",
        table_name="routes",
        keep_files=True,
    )


def test_cli_requires_department(monkeypatch) -> None:
    """Le département est obligatoire et aucune opération ne démarre sans lui."""
    from cli.app import app
    from cli.commands import bdtopo

    run_flow = MagicMock()
    monkeypatch.setattr(bdtopo, "import_bdtopo_troncon_route_flow", run_flow)
    result = CliRunner().invoke(app, ["bdtopo-troncon-route"])
    assert result.exit_code == 2
    run_flow.assert_not_called()


@pytest.mark.parametrize(
    ("department", "edition_date"),
    [("35,22", None), ("35", "2026-99-99")],
)
def test_flow_rejects_invalid_input_before_io(
    monkeypatch, tmp_path, department, edition_date
) -> None:
    """Refuse les entrées invalides avant tout accès réseau, disque ou base."""
    find = MagicMock()
    monkeypatch.setattr(route_import, "find_geopf_resource", find)
    directory = tmp_path / "downloads"
    monkeypatch.setattr(route_import, "DOWNLOAD_DIR", directory)
    with pytest.raises(ValueError):
        route_import.import_bdtopo_troncon_route_flow.fn(department, edition_date)
    find.assert_not_called()
    assert not directory.exists()
