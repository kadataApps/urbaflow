import logging
import os
from pathlib import Path
from prefect import get_run_logger

from shared_tasks.config import APP_DIR


def setup_logging():
    """Configure logging for the entire application"""
    log_level = int(os.getenv("LOG_LEVEL", logging.INFO))
    log_dir = os.getenv("LOG_DIR", APP_DIR / "../logs")
    log_filepath = log_dir / "urbaflow.log"
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Add to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str = None):
    """Get a logger for the calling module"""
    try:
        # In Prefect context, use Prefect logger
        return get_run_logger()
    except Exception:
        # Outside Prefect, use regular logger with module name
        return logging.getLogger(name or __name__)
