"""Logging configuration with per-run traceability."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Mapping
from typing import Any, Final

EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LONG_NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b\d{6,}\b")


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive values from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact_value(record.msg)
        if isinstance(record.args, Mapping):
            record.args = {key: _redact_value(value) for key, value in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(_redact_value(value) for value in record.args)
        return True


class RunIdFilter(logging.Filter):
    """Ensures every log record contains a run ID."""

    def __init__(self, run_id: str) -> None:
        super().__init__()
        self._run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = self._run_id
        return True


def configure_logging(run_id: str | None = None, level: int = logging.INFO) -> str:
    """Configure root logging for an automation run.

    Args:
        run_id: Existing run ID, or None to generate a UUID.
        level: Root logging level.

    Returns:
        The run ID applied to all log records.

    Raises:
        ValueError: If the supplied run ID is blank.
    """
    resolved_run_id = run_id or str(uuid.uuid4())
    if not resolved_run_id.strip():
        raise ValueError("run_id cannot be blank")

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(_build_formatter())
    handler.addFilter(SensitiveDataFilter())
    handler.addFilter(RunIdFilter(resolved_run_id))
    root_logger.addHandler(handler)
    return resolved_run_id


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s %(levelname)s run_id=%(run_id)s %(name)s - %(message)s"
    )


def _redact_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    without_emails = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    return LONG_NUMBER_PATTERN.sub("[REDACTED_NUMBER]", without_emails)
