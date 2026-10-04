"""
Logging Configuration.
Initializes custom logging format and routing for the application.
"""

import json
import logging
import sys

from app.core.config import settings


class JSONLogFormatter(logging.Formatter):
    """
    JSON structured log formatter for production log ingestion.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the specified record as a JSON object string.
        """
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging() -> None:
    """
    Configure application logging.
    Enforces structured JSON logging in production and readable console formatting in other environments.
    """
    handler = logging.StreamHandler(sys.stdout)
    if settings.ENVIRONMENT.lower() == "production":
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
