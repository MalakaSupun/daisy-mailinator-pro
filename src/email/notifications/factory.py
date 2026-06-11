"""Factory helpers for DaisyBill notification services."""

from __future__ import annotations

from email.config.settings import EmailSettings, load_email_settings
from email.notifications.graph_email_client import GraphEmailClient
from email.notifications.idempotency import EmailCheckpointStore
from email.notifications.notification_service import DaisyBillNotificationService


def build_notification_service(settings: EmailSettings | None = None) -> DaisyBillNotificationService:
    """Build a configured DaisyBill notification service.

    Args:
        settings: Optional pre-loaded settings. Environment settings are loaded when omitted.

    Returns:
        Configured notification service.

    Raises:
        SettingsError: If environment configuration is invalid.
    """
    resolved_settings = settings or load_email_settings()
    checkpoint_store = EmailCheckpointStore(resolved_settings.checkpoint_path)
    email_client = GraphEmailClient(resolved_settings, checkpoint_store)
    return DaisyBillNotificationService(resolved_settings, email_client)
