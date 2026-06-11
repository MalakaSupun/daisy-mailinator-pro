"""Application settings loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final
import os

from dotenv import load_dotenv

DEFAULT_ENV_FILE: Final[Path] = Path(".env")


class SettingsError(ValueError):
    """Raised when required application settings are missing or invalid."""


@dataclass(frozen=True, slots=True)
class EmailSettings:
    """Email and Microsoft Graph configuration."""

    from_address: str
    to_addresses: tuple[str, ...]
    cc_addresses: tuple[str, ...]
    client_id: str
    tenant_id: str
    client_secret: str
    authority: str
    scopes: tuple[str, ...]
    timeout_seconds: int
    checkpoint_path: Path


def load_email_settings(env_file: Path = DEFAULT_ENV_FILE) -> EmailSettings:
    """Load email settings from environment variables.

    Args:
        env_file: Optional dotenv file path to load before reading variables.

    Returns:
        Validated email settings.

    Raises:
        SettingsError: If required settings are missing or invalid.
    """
    if env_file.exists():
        load_dotenv(env_file)

    timeout_seconds = _read_positive_int("MS_GRAPH_TIMEOUT_SECONDS", default=30)
    checkpoint_path = Path(_read_optional("EMAIL_CHECKPOINT_PATH", "output/email_checkpoint.json"))

    settings = EmailSettings(
        from_address=_read_required("EMAIL_FROM_ADDRESS"),
        to_addresses=_read_email_list("EMAIL_TO_ADDRESSES"),
        cc_addresses=_read_email_list("EMAIL_CC_ADDRESSES", required=False),
        client_id=_read_required("MS_GRAPH_CLIENT_ID"),
        tenant_id=_read_required("MS_GRAPH_TENANT_ID"),
        client_secret=_read_required("MS_GRAPH_CLIENT_SECRET"),
        authority=_read_required("MS_GRAPH_AUTHORITY"),
        scopes=_read_csv("MS_GRAPH_SCOPE"),
        timeout_seconds=timeout_seconds,
        checkpoint_path=checkpoint_path,
    )
    _validate_authority(settings.authority, settings.tenant_id)
    return settings


def _read_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SettingsError(f"Missing required environment variable: {name}")
    return value


def _read_optional(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def _read_csv(name: str, required: bool = True) -> tuple[str, ...]:
    raw_value = os.getenv(name, "").strip()
    values = tuple(item.strip() for item in raw_value.split(",") if item.strip())
    if required and not values:
        raise SettingsError(f"Missing required environment variable: {name}")
    return values


def _read_email_list(name: str, required: bool = True) -> tuple[str, ...]:
    emails = _read_csv(name, required=required)
    invalid_emails = [email for email in emails if "@" not in email or email.startswith("@")]
    if invalid_emails:
        raise SettingsError(f"Invalid email address configured in {name}")
    return emails


def _read_positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed_value = int(raw_value)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer") from exc
    if parsed_value <= 0:
        raise SettingsError(f"{name} must be greater than zero")
    return parsed_value


def _validate_authority(authority: str, tenant_id: str) -> None:
    expected_suffix = f"/{tenant_id}".lower()
    if not authority.lower().endswith(expected_suffix):
        raise SettingsError("MS_GRAPH_AUTHORITY must end with the configured tenant ID")
