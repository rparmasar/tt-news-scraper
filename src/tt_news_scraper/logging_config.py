import logging
from rich.logging import RichHandler
import sys


def setup_logging(level: int = logging.INFO):
    """Configure logging with console and file handlers."""

    logger = logging.getLogger("tt_news_scraper")
    logger.setLevel(level)
    logger.handlers.clear()

    # Console handler (Rich-formatted for terminal output)
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=False,  # Disable timestamp in console output
        markup=True,      # Enable ANSI color codes
    )
    console_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    ))

    # File handler for detailed logs (always active)
    file_handler = logging.FileHandler("tt_scraper.log")
    file_handler.setLevel(logging.DEBUG)  # Capture all details in file
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Singleton instance for imports
logger = setup_logging()
