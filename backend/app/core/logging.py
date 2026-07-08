"""
Logging Configuration.
Initializes custom logging format and routing for the application.
"""

import logging
import sys


def setup_logging() -> None:
    """
    Configure the default application logs format.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
