"""
Structured Logging Configuration.
Provides structured JSON logging using structlog and standard library logging integration,
with automatic trace ID correlation and binary payload sanitization.
"""

import json
import logging
import sys
from collections.abc import Mapping
from typing import Any

import structlog

from app.core.config import settings
from app.core.tracing import get_trace_id

# Standard LogRecord attributes to exclude from extra key extraction
STANDARD_LOGRECORD_ATTRS: set[str] = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def sanitize_binary_data(val: Any) -> Any:
    """
    Recursively sanitize objects for logging to ensure binary data,
    file streams, and raw bytes are never dumped into the logs.

    Args:
        val: The object or value to sanitize.

    Returns:
        Sanitized safe representation.
    """
    if isinstance(val, (bytes, bytearray, memoryview)):
        return f"<binary data: {len(val)} bytes>"
    if hasattr(val, "read") and hasattr(val, "filename"):
        return f"<{val.__class__.__name__} filename={getattr(val, 'filename', 'unnamed')}>"
    if isinstance(val, str) and "\x00" in val:
        return f"<binary string: {len(val)} chars>"
    if isinstance(val, Mapping):
        return {str(k): sanitize_binary_data(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        sanitized_items = [sanitize_binary_data(item) for item in val]
        return type(val)(sanitized_items) if isinstance(val, (list, tuple)) else sanitized_items
    return val


def _sanitize_binary_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that sanitizes binary data in all event dictionary values."""
    return {k: sanitize_binary_data(v) for k, v in event_dict.items()}


def _add_trace_id_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that guarantees the active trace_id is attached to every event."""
    active_trace_id = get_trace_id()
    if active_trace_id and "trace_id" not in event_dict:
        event_dict["trace_id"] = active_trace_id
    return event_dict


class JSONLogFormatter(logging.Formatter):
    """
    JSON structured log formatter for production log ingestion and distributed tracing.
    Ensures every log entry includes timestamp, level, module, message, trace_id,
    and sanitized context metadata without leaking binary payloads.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the specified record as a valid structured JSON string.
        """
        active_trace = getattr(record, "trace_id", None) or get_trace_id()

        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        if active_trace:
            log_obj["trace_id"] = active_trace

        # Extract custom extra attributes attached to the LogRecord
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOGRECORD_ATTRS and key not in log_obj:
                log_obj[key] = sanitize_binary_data(value)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class StructuredLogger(logging.Logger):
    """
    Custom Logger subclass compatible with standard logging.Logger and structlog.
    Supports .bind(**kwargs) for scoped context and arbitrary keyword arguments in log calls.
    """

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        self._bound_context: dict[str, Any] = {}

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """
        Create a new StructuredLogger instance inheriting current context merged with kwargs.

        Returns:
            StructuredLogger: A bound logger instance with the attached context.
        """
        new_logger = StructuredLogger(self.name, self.level)
        new_logger._bound_context = {**self._bound_context, **kwargs}
        new_logger.parent = self.parent
        new_logger.handlers = self.handlers
        new_logger.propagate = self.propagate
        new_logger.disabled = self.disabled
        return new_logger

    def unbind(self, *keys: str) -> "StructuredLogger":
        """
        Create a new StructuredLogger instance with specified keys removed from bound context.
        """
        new_logger = StructuredLogger(self.name, self.level)
        new_logger._bound_context = {k: v for k, v in self._bound_context.items() if k not in keys}
        new_logger.parent = self.parent
        new_logger.handlers = self.handlers
        new_logger.propagate = self.propagate
        new_logger.disabled = self.disabled
        return new_logger

    def _log(
        self,
        level: int,
        msg: object,
        args: Any,
        exc_info: Any = None,
        extra: Mapping[str, object] | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        **kwargs: Any,
    ) -> None:
        """
        Intercept logging calls to merge bound context and arbitrary keyword arguments
        into extra dictionary, sanitizing binary data and attaching trace ID.
        """
        merged_extra: dict[str, Any] = dict(self._bound_context)
        if extra:
            merged_extra.update(extra)
        if kwargs:
            merged_extra.update(kwargs)

        active_trace = get_trace_id()
        if active_trace and "trace_id" not in merged_extra:
            merged_extra["trace_id"] = active_trace

        sanitized_extra = sanitize_binary_data(merged_extra)
        # Safeguard against standard LogRecord attribute collisions (e.g. filename, module, name)
        safe_extra: dict[str, Any] = {}
        for k, v in sanitized_extra.items():
            if k in STANDARD_LOGRECORD_ATTRS:
                safe_extra[f"custom_{k}"] = v
            else:
                safe_extra[k] = v

        super()._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            extra=safe_extra,
            stack_info=stack_info,
            stacklevel=stacklevel,
        )


def setup_logging() -> None:
    """
    Configure application logging and structlog.
    Enforces structured JSON logging in production and readable formatting in development,
    registering StructuredLogger as the default logger class.
    """
    # Register custom logger class for all subsequent logging.getLogger() calls
    logging.setLoggerClass(StructuredLogger)

    # Configure structlog processors and factory
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_trace_id_processor,
            _sanitize_binary_processor,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    if settings.ENVIRONMENT.lower() == "production":
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def get_logger(name: str = "") -> StructuredLogger:
    """
    Retrieve a StructuredLogger instance by module name.

    Args:
        name: The logger name (typically __name__).

    Returns:
        StructuredLogger: An initialized structured logger.
    """
    logger = logging.getLogger(name or "app")
    if not isinstance(logger, StructuredLogger):
        # Fallback cast or wrap if logger was already created before setLoggerClass
        wrapper = StructuredLogger(name or "app", logger.level)
        wrapper.parent = logger.parent
        wrapper.handlers = logger.handlers
        return wrapper
    return logger
