import inspect
from unittest.mock import MagicMock

import pytest
from cli.app import app
from typer.main import get_command
from typer.testing import CliRunner

DEPARTMENT_COMMANDS = [
    ("risques-cavite", "import_risques_cavite_flow", "department"),
    ("risques-rga", "import_rga_flow", "department"),
    ("risques-remnappes", "import_remnappes_flow", "department"),
    ("risques-mvt", "import_risques_mvt_flow", "department"),
    ("risques-casias", "import_risques_casias_flow", "department"),
    ("risques-sis", "import_risques_sis_flow", "department"),
    ("risques-sup", "import_risques_sup_flow", "department"),
    ("risques-tri", "import_tri_flow", "department"),
    ("bpe", "import_bpe_flow", "department"),
    ("geosirene", "import_geosirene_data", "department"),
    ("sirene-etablissement", "import_sirene_etablissement_data", "department"),
    ("bdtopo-batiment", "import_bdtopo_batiment_flow", "departements"),
    ("bdtopo-troncon-route", "import_bdtopo_troncon_route_flow", "department"),
    ("ocsge", "import_ocsge_flow", "departements"),
]

RECREATE_DEFAULTS = {
    "lovac-fil": True,
    "risques-cavite": True,
    "risques-rga": False,
    "risques-remnappes": False,
    "risques-mvt": False,
    "risques-casias": False,
    "risques-sis": False,
    "risques-sup": False,
    "risques-tri": False,
    "risques-icpe": False,
    "risques-irep": False,
    "risques-gaspar": False,
    "gpu-sup": True,
    "banatic-communes": True,
    "bdtopo-batiment": False,
    "ocsge": False,
    "docurba-epci": False,
    "bpe": True,
    "mh": True,
    "acr": True,
    "geosirene": True,
    "sirene-etablissement": True,
    "geosirene-detail": True,
    "cartofriches": True,
}

COMMAND_NAMES = set(RECREATE_DEFAULTS) | {
    "install-base-functions",
    "dvf",
    "dgfip-topo",
    "dgfip-geoparquet",
    "locomvac",
    "lovac",
    "majic",
    "bdtopo-troncon-route",
    "epci-gpu",
    "gpu-plu",
}


@pytest.mark.parametrize("option", ["-d", "--departement", "--department"])
@pytest.mark.parametrize(
    ("command_name", "flow_name", "parameter"), DEPARTMENT_COMMANDS
)
def test_department_aliases(monkeypatch, command_name, flow_name, parameter, option):
    """Vérifie les trois alias et la transmission du code sans exécuter de flow."""
    run_flow = MagicMock()
    command = get_command(app).commands[command_name]
    command_module = inspect.getmodule(inspect.unwrap(command.callback))
    monkeypatch.setattr(command_module, flow_name, run_flow)

    result = CliRunner().invoke(app, [command_name, option, "2A"])

    assert result.exit_code == 0, result.output
    run_flow.assert_called_once()
    assert run_flow.call_args.kwargs[parameter] == "2A"


def test_recreate_defaults():
    """Fige les valeurs historiques de recreate pour toutes les commandes."""
    commands = get_command(app).commands
    actual = {
        command_name: parameter.default
        for command_name, command in commands.items()
        for parameter in command.params
        if parameter.name == "recreate"
    }

    assert actual == RECREATE_DEFAULTS


def test_command_names():
    """Conserve toutes les commandes à la racine, sans groupes supplémentaires."""
    assert set(get_command(app).commands) == COMMAND_NAMES


@pytest.mark.parametrize("command_name", sorted(COMMAND_NAMES))
def test_command_help(command_name):
    """Vérifie que chaque commande reste accessible et expose son aide."""
    result = CliRunner().invoke(app, [command_name, "--help"])

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    ("command_name", "flow_name", "parameter"), DEPARTMENT_COMMANDS[:8]
)
def test_missing_directory_and_department(
    monkeypatch, command_name, flow_name, parameter
):
    """Refuse une commande Géorisques sans source avant d'appeler le flow."""
    run_flow = MagicMock()
    command = get_command(app).commands[command_name]
    command_module = inspect.getmodule(inspect.unwrap(command.callback))
    monkeypatch.setattr(command_module, flow_name, run_flow)

    result = CliRunner().invoke(app, [command_name])

    assert result.exit_code == 1
    assert "--departement" in result.output
    run_flow.assert_not_called()
