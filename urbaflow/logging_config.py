import logging
import os

log_level = os.getenv("LOG_LEVEL", logging.DEBUG)

# Get log file path from environment variable (default None)
log_filepath = os.getenv("LOG_FILE")

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
