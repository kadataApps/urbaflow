from unittest.mock import MagicMock

import pytest
import requests
from cli.app import app
from cli.commands import sitadel as sitadel_command
from flows.sitadel import download_sitadel
from typer.testing import CliRunner

EXPECTED_FILENAMES = {
    "sitadel_communes_logements_annuels.csv",
    "sitadel_communes_logements_mensuels.csv",
    "sitadel_communes_locaux_annuels.csv",
    "sitadel_communes_locaux_mensuels.csv",
    "sitadel_detail_logements.csv",
    "sitadel_detail_locaux.csv",
    "sitadel_detail_permis_amenager.csv",
    "sitadel_detail_permis_demolir.csv",
}


def test_download_all_sitadel_files(monkeypatch, tmp_path):
    """Récupère les huit exports complets en streaming et rafraîchit les fichiers."""
    destination = tmp_path / "sitadel"
    destination.mkdir()
    for filename in EXPECTED_FILENAMES:
        (destination / filename).write_bytes(b"ancien")
    response = MagicMock()
    response.headers = {"Content-Length": "6"}
    response.iter_content.side_effect = lambda **kwargs: iter([b"rec", b"ent"])
    response.__enter__.return_value = response
    get_response = MagicMock(return_value=response)
    monkeypatch.setattr("shared_tasks.etl_file_utils.requests.get", get_response)

    paths = download_sitadel.download_sitadel_flow.fn(destination)

    assert {path.name for path in paths} == EXPECTED_FILENAMES
    assert len(paths) == len(EXPECTED_FILENAMES)
    assert {path.name for path in destination.iterdir()} == EXPECTED_FILENAMES
    assert all(path.read_bytes() == b"recent" for path in paths)
    assert get_response.call_count == len(EXPECTED_FILENAMES)
    assert len({call.args[0] for call in get_response.call_args_list}) == 8
    for call in get_response.call_args_list:
        assert call.args[0].startswith(download_sitadel.DIDO_DATAFILES_URL + "/")
        assert call.args[0].endswith("/csv")
        assert call.kwargs == {"stream": True, "timeout": (30, 300)}
    assert response.raise_for_status.call_count == 8


def test_default_destination(monkeypatch, tmp_path):
    """Crée le répertoire temporaire SITADEL sans paramètre explicite."""
    monkeypatch.setattr(download_sitadel, "TEMP_DIR", tmp_path)

    def write_download(**kwargs):
        """Simule un export CSV téléchargé."""
        kwargs["target_path"].write_bytes(b"code;valeur\n01001;1\n")

    monkeypatch.setattr(download_sitadel, "download_file", write_download)

    paths = download_sitadel.download_sitadel_flow.fn()

    assert len(paths) == 8
    assert all(path.parent == tmp_path / "sitadel" for path in paths)


@pytest.mark.parametrize("existing_file", [False, True])
@pytest.mark.parametrize("failure", ["http", "interrupted", "empty"])
def test_failed_download_preserves_destination(
    monkeypatch, tmp_path, existing_file, failure
):
    """Propage l'échec, préserve l'ancien fichier et supprime le fichier partiel."""
    filename = next(iter(download_sitadel.SITADEL_DATAFILES))
    target_path = tmp_path / filename
    if existing_file:
        target_path.write_bytes(b"ancien")
    response = MagicMock()
    response.headers = {}
    response.__enter__.return_value = response
    if failure == "http":
        response.raise_for_status.side_effect = requests.HTTPError("Erreur HTTP 503")
        expected_error = requests.HTTPError
    elif failure == "interrupted":

        def interrupted_chunks(**kwargs):
            """Interrompt le transfert après un premier bloc."""
            yield b"partiel"
            raise requests.ConnectionError("Connexion interrompue")

        response.iter_content.side_effect = interrupted_chunks
        expected_error = requests.ConnectionError
    else:
        response.iter_content.return_value = iter([])
        expected_error = ValueError
    get_response = MagicMock(return_value=response)
    monkeypatch.setattr("shared_tasks.etl_file_utils.requests.get", get_response)

    with pytest.raises(expected_error):
        download_sitadel.download_sitadel_flow.fn(tmp_path)

    get_response.assert_called_once()
    assert list(tmp_path.iterdir()) == ([target_path] if existing_file else [])
    if existing_file:
        assert target_path.read_bytes() == b"ancien"


@pytest.mark.parametrize("explicit_directory", [False, True])
def test_sitadel_cli(monkeypatch, tmp_path, explicit_directory):
    """Transmet la destination au flow, y compris si elle n'existe pas encore."""
    run_flow = MagicMock()
    monkeypatch.setattr(sitadel_command, "download_sitadel_flow", run_flow)
    destination = tmp_path / "nouveau"
    arguments = ["sitadel"]
    if explicit_directory:
        arguments.append(str(destination))

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0, result.output
    run_flow.assert_called_once_with(
        dirname=destination if explicit_directory else None
    )


def test_sitadel_cli_rejects_file(monkeypatch, tmp_path):
    """Refuse une destination qui désigne un fichier avant de lancer le flow."""
    run_flow = MagicMock()
    monkeypatch.setattr(sitadel_command, "download_sitadel_flow", run_flow)
    destination = tmp_path / "fichier.csv"
    destination.touch()

    result = CliRunner().invoke(app, ["sitadel", str(destination)])

    assert result.exit_code != 0
    run_flow.assert_not_called()


def test_sitadel_cli_propagates_failure(monkeypatch):
    """Retourne un code d'échec si un téléchargement échoue."""
    monkeypatch.setattr(
        sitadel_command,
        "download_sitadel_flow",
        MagicMock(side_effect=requests.HTTPError("Erreur HTTP 503")),
    )

    result = CliRunner().invoke(app, ["sitadel"])

    assert result.exit_code != 0
    assert isinstance(result.exception, requests.HTTPError)
