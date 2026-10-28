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

RECREATE_FLOW_NAMES = {
    name: flow_name
    for name, flow_name, _ in DEPARTMENT_COMMANDS
    if name in RECREATE_DEFAULTS
} | {
    "lovac-fil": "import_lovac_fil_flow",
    "risques-icpe": "import_icpe_flow",
    "risques-irep": "import_risques_irep_flow",
    "risques-gaspar": "import_risques_gaspar_flow",
    "gpu-sup": "import_gpu_sup_flow",
    "banatic-communes": "import_banatic_communes_flow",
    "docurba-epci": "import_docurba_documents_flow",
    "mh": "import_mh_flow",
    "acr": "import_acr_flow",
    "geosirene-detail": "create_geosirene_etablissement_detail",
    "cartofriches": "import_cartofriches_flow",
}

REPLACE_PARAMETER_COMMANDS = {
    "risques-rga",
    "risques-remnappes",
    "risques-tri",
    "risques-icpe",
    "gpu-sup",
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


@pytest.mark.parametrize("with_department", [False, True])
@pytest.mark.parametrize(
    ("command_name", "flow_name", "parameter"), DEPARTMENT_COMMANDS[:8]
)
def test_directory_source(
    monkeypatch, tmp_path, command_name, flow_name, parameter, with_department
):
    """Accepte un répertoire seul ou accompagné d'un département, comme auparavant."""
    run_flow = MagicMock()
    command = get_command(app).commands[command_name]
    command_module = inspect.getmodule(inspect.unwrap(command.callback))
    monkeypatch.setattr(command_module, flow_name, run_flow)
    arguments = [command_name, str(tmp_path)]
    if with_department:
        arguments.extend(["--departement", "35"])

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0, result.output
    run_flow.assert_called_once()
    directory_parameter = (
        "dirname"
        if command_name in {"risques-rga", "risques-remnappes", "risques-tri"}
        else "path"
    )
    assert run_flow.call_args.kwargs[directory_parameter] == tmp_path
    assert run_flow.call_args.kwargs[parameter] == ("35" if with_department else None)


@pytest.mark.parametrize("recreate", [None, True, False])
@pytest.mark.parametrize("command_name", sorted(RECREATE_DEFAULTS))
def test_recreate_forwarding(monkeypatch, tmp_path, command_name, recreate):
    """Vérifie les valeurs par défaut et les deux drapeaux jusqu'aux flows."""
    run_flow = MagicMock()
    command = get_command(app).commands[command_name]
    command_module = inspect.getmodule(inspect.unwrap(command.callback))
    monkeypatch.setattr(command_module, RECREATE_FLOW_NAMES[command_name], run_flow)
    arguments = [command_name]
    if command_name == "lovac-fil":
        arguments.append(str(tmp_path))
    elif command_name == "docurba-epci":
        arguments.append("200071629")
    elif command_name in {name for name, _, _ in DEPARTMENT_COMMANDS}:
        arguments.extend(["--departement", "35"])
    if recreate is not None:
        arguments.append("--recreate" if recreate else "--no-recreate")

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0, result.output
    run_flow.assert_called_once()
    parameter = "replace" if command_name in REPLACE_PARAMETER_COMMANDS else "recreate"
    expected = RECREATE_DEFAULTS[command_name] if recreate is None else recreate
    assert run_flow.call_args.kwargs[parameter] is expected
