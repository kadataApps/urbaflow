from pathlib import Path

from cli.app import app
from dotenv import load_dotenv
from shared_tasks.logging_config import setup_logging

load_dotenv(Path(__file__).parent.parent.parent / ".env")
setup_logging()


if __name__ == "__main__":
    app()
