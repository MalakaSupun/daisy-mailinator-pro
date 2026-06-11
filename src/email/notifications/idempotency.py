"""Idempotency checkpoint store for email sends."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.email.config.logging_config import configure_logging

run_id = configure_logging()

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmailCheckpointStore:
    """JSON-backed checkpoint store for sent email idempotency keys."""

    checkpoint_path: Path

    def has_sent(self, idempotency_key: str) -> bool:
        """Check whether an email idempotency key has already been recorded.

        Args:
            idempotency_key: Deterministic key for a business email event.

        Returns:
            True when the key already exists in the checkpoint store.

        Raises:
            OSError: If the checkpoint file cannot be read.
            json.JSONDecodeError: If the checkpoint file is corrupt.
        """
        checkpoint_data = self._load_checkpoint_data()
        return idempotency_key in checkpoint_data.get("sent_email_keys", {})

    def mark_sent(self, idempotency_key: str) -> None:
        """Persist that an email idempotency key was sent successfully.

        Args:
            idempotency_key: Deterministic key for a business email event.

        Returns:
            None.

        Raises:
            OSError: If the checkpoint file cannot be written.
            json.JSONDecodeError: If the checkpoint file is corrupt.
        """
        checkpoint_data = self._load_checkpoint_data()
        sent_email_keys = checkpoint_data.setdefault("sent_email_keys", {})
        sent_email_keys[idempotency_key] = datetime.now(timezone.utc).isoformat()
        self._write_checkpoint_data(checkpoint_data)
        LOGGER.info("Email checkpoint updated")

    def _load_checkpoint_data(self) -> dict[str, dict[str, str]]:
        if not self.checkpoint_path.exists():
            return {"sent_email_keys": {}}
        with self.checkpoint_path.open("r", encoding="utf-8") as checkpoint_file:
            loaded_data = json.load(checkpoint_file)
        if not isinstance(loaded_data, dict):
            raise json.JSONDecodeError("Checkpoint root must be an object", "", 0)
        return loaded_data

    def _write_checkpoint_data(self, checkpoint_data: dict[str, dict[str, str]]) -> None:
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=self.checkpoint_path.parent) as temp_file:
            json.dump(checkpoint_data, temp_file, indent=2, sort_keys=True)
            temp_path = Path(temp_file.name)
        temp_path.replace(self.checkpoint_path)
