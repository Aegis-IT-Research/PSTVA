import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Optional


request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def new_request_id() -> str:
    return uuid.uuid4().hex


def setup_logging() -> None:
    """Configure root logging once for API + workers.

    Logs go to stdout so `docker compose logs` is the single source of truth.
    """

    level_name = os.environ.get("AEGIS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()

    # Idempotent: if already configured, don't double-add handlers/filters.
    if getattr(root, "_aegis_logging_configured", False):
        return

    # Ensure every record has request_id to avoid formatter KeyError.
    if not getattr(root, "_aegis_record_factory_set", False):
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            if not hasattr(record, "request_id"):
                record.request_id = request_id_var.get("-")
            return record

        logging.setLogRecordFactory(record_factory)
        root._aegis_record_factory_set = True

    root.setLevel(level)

    handler = logging.StreamHandler(stream=sys.stdout)

    if os.environ.get("AEGIS_LOG_FORMAT", "text").lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)
    root.addFilter(RequestIdFilter())

    # Make common noisy loggers slightly calmer by default.
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(
            os.environ.get("AEGIS_ACCESS_LOG_LEVEL", "INFO").upper()
        )

    root._aegis_logging_configured = True


def set_request_id(request_id: Optional[str]) -> Any:
    """Set request id in contextvars; returns token for reset."""

    return request_id_var.set(request_id or "-")


def reset_request_id(token: Any) -> None:
    request_id_var.reset(token)
