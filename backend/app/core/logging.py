"""Production diagnostics without request payloads, SQL values or tracebacks."""

import json
import logging
import re


class SafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Application events are identifiers; arbitrary dependency messages may
        # contain URLs, credentials or provider payloads and are not reproduced.
        event = record.msg if isinstance(record.msg, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", record.msg) else "runtime_log"
        data = {"level": record.levelname, "logger": record.name, "event": event}
        for key in ("request_id", "request_type", "handler_type", "transactional",
                    "outcome", "duration_ms", "target_date", "processed_count", "created_count"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data["error_type"] = record.exc_info[0].__name__
        return json.dumps(data, default=str)


def production_log_config() -> dict:
    return {
        "version": 1, "disable_existing_loggers": False,
        "formatters": {"safe": {"()": SafeJsonFormatter}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe"}},
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {name: {"handlers": [], "propagate": True, "level": "INFO"}
                    for name in ("uvicorn", "uvicorn.error", "uvicorn.access")},
    }
