"""Tests du téléchargement optionnel et de la commande DGFiP TOPO."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from cli.app import app
from cli.commands import cadastre
from flows.cadastre import flow_dgfip_topo
from flows.cadastre.tasks.import_dgfip_topo import SOURCE_FILENAME
from requests import HTTPError
from typer.testing import CliRunner


@pytest.fixture
def flow_steps(monkeypatch, tmp_path):
    """Isole le flux des accès réseau, disque et base de données."""
    monkeypatch.setattr(flow_dgfip_topo, "TEMP_DIR", tmp_path)
    steps = Mock()
    for name in (
        "download_file",
        "copy_directory",
        "import_dgfip_topo_file",
        "create_dgfip_topo_tables",
        "format_dgfip_topo_data",
    ):
        monkeypatch.setattr(flow_dgfip_topo, name, getattr(steps, name))
    return steps


@pytest.mark.parametrize("use_local_directory", [False, True])
def test_flow_source(flow_steps, tmp_path, use_local_directory):
    """Télécharge uniquement sans répertoire et conserve les étapes d'import."""
    source_dir = tmp_path / "source" if use_local_directory else None

    flow_dgfip_topo.import_dgfip_topo_flow.fn(path=source_dir)

    if use_local_directory:
        flow_steps.download_file.assert_not_called()
    else:
        source_dir = tmp_path / "dgfip_topo"
        flow_steps.download_file.assert_called_once_with(
            url=flow_dgfip_topo.DEFAULT_SOURCE_URL,
            target_path=source_dir / SOURCE_FILENAME,
        )
    flow_steps.copy_directory.assert_called_once_with(
        flow_dgfip_topo.QUERIES_DIR / "dgfip_topo", tmp_path / "sql"
    )
    flow_steps.import_dgfip_topo_file.assert_called_once_with(source_dir=source_dir)
    flow_steps.create_dgfip_topo_tables.assert_called_once_with()
    flow_steps.format_dgfip_topo_data.assert_called_once_with()


def test_download_failure_stops_import(flow_steps):
    """Propage les erreurs de téléchargement avant toute opération en base."""
    flow_steps.download_file.side_effect = HTTPError("Échec du téléchargement")

    with pytest.raises(HTTPError, match="Échec du téléchargement"):
        flow_dgfip_topo.import_dgfip_topo_flow.fn()

    flow_steps.copy_directory.assert_not_called()
    flow_steps.import_dgfip_topo_file.assert_not_called()
    flow_steps.create_dgfip_topo_tables.assert_not_called()
    flow_steps.format_dgfip_topo_data.assert_not_called()


@pytest.mark.parametrize("use_local_directory", [False, True])
def test_cli_source(monkeypatch, tmp_path, use_local_directory):
    """Transmet le répertoire explicite ou None au flux depuis la commande."""
    import_flow = Mock()
    monkeypatch.setattr(cadastre, "import_dgfip_topo_flow", import_flow)
    arguments = ["dgfip-topo"]
    if use_local_directory:
        arguments.append(str(tmp_path))

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0, result.output
    import_flow.assert_called_once_with(
        path=tmp_path.resolve() if use_local_directory else None
    )


@pytest.mark.parametrize("invalid_path_type", ["missing", "file"])
def test_cli_rejects_invalid_directory(monkeypatch, tmp_path, invalid_path_type):
    """Refuse les chemins inexistants et les fichiers sans lancer le flux."""
    import_flow = Mock()
    monkeypatch.setattr(cadastre, "import_dgfip_topo_flow", import_flow)
    source_path: Path = tmp_path / invalid_path_type
    if invalid_path_type == "file":
        source_path.touch()

    result = CliRunner().invoke(app, ["dgfip-topo", str(source_path)])

    assert result.exit_code == 2, result.output
    import_flow.assert_not_called()
