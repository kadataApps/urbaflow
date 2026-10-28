import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from cli import bootstrap


def test_main_import_has_no_startup_side_effects(tmp_path):
    """Importe le point d'entrée sans charger de flow ni initialiser les logs."""
    package_directory = Path(__file__).resolve().parents[1] / "urbaflow"
    environment = {
        **os.environ,
        "PYTHONPATH": str(package_directory),
        "LOG_DIR": str(tmp_path / "logs"),
    }

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import dotenv; from unittest.mock import Mock; "
                "dotenv.load_dotenv = Mock(side_effect=AssertionError("
                "'Chargement inattendu du .env')); import main; "
                "assert 'cli.app' not in sys.modules; "
                "assert 'shared_tasks.logging_config' not in sys.modules; "
                "assert not any(name.startswith('flows') for name in sys.modules)"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""
    assert not (tmp_path / "logs").exists()


def test_run_cli_initialization_order(monkeypatch):
    """Charge le .env racine, configure les logs puis importe les commandes."""
    events = []
    application_module = ModuleType("cli.app")
    application_module.app = lambda: events.append("run")
    logging_module = ModuleType("shared_tasks.logging_config")
    logging_module.setup_logging = lambda: events.append("logging")
    original_import = __import__

    def track_import(name, *args, **kwargs):
        """Observe les imports différés sans exécuter de traitement."""
        if name == "shared_tasks.logging_config":
            events.append("import_logging")
            return logging_module
        if name == "cli.app":
            events.append("import_app")
            return application_module
        return original_import(name, *args, **kwargs)

    load_environment = MagicMock(side_effect=lambda path: events.append("dotenv"))
    monkeypatch.setattr(bootstrap, "load_dotenv", load_environment)
    monkeypatch.setattr("builtins.__import__", track_import)

    bootstrap.run_cli()

    load_environment.assert_called_once_with(
        Path(__file__).resolve().parents[2] / ".env"
    )
    assert events == ["dotenv", "import_logging", "logging", "import_app", "run"]


def test_run_cli_propagates_initialization_errors(monkeypatch):
    """Ne transforme pas une erreur de démarrage en succès apparent."""
    monkeypatch.setattr(
        bootstrap,
        "load_dotenv",
        MagicMock(side_effect=OSError("Impossible de charger l'environnement")),
    )

    with pytest.raises(OSError, match="Impossible de charger l'environnement"):
        bootstrap.run_cli()
