import logging
import os
from prefect import get_run_logger
from contextlib import suppress

log_level = os.getenv("LOG_LEVEL", logging.DEBUG)

# Get log file path from environment variable (default None)
log_filepath = os.path.join(os.getcwd(), "../logs/urbaflow.log")

# Configure logging
logging.basicConfig(
    filename=log_filepath,
    level=log_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Ensure console handler exists (prevents issues if not set in env var)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Set console log level to DEBUG (always print)
logger.addHandler(console_handler)

def get_logger():
    with suppress(Exception):
        return get_run_logger() 
    return logger