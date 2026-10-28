from pathlib import Path

from dotenv import load_dotenv


def run_cli() -> None:
    """Charge l'environnement et les logs avant d'importer et lancer les commandes."""
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")

    from shared_tasks.logging_config import setup_logging

    setup_logging()

    from cli.app import app

    app()
