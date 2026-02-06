"""Structured logging utilities with request context."""

import json
import logging
import os
from datetime import datetime, timezone
import contextvars

request_id_ctx = contextvars.ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = request_id_ctx.get()
        if request_id:
            log_entry["request_id"] = request_id

        # Include any extra fields added to the record
        reserved = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName", "processName",
            "process", "message"
        }
        for key, value in record.__dict__.items():
            if key not in reserved:
                log_entry[key] = value

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON formatting."""
    log_level = os.getenv("LOG_LEVEL", level).upper()
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Replace handlers to avoid duplicate logs
    root_logger.handlers = []
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
