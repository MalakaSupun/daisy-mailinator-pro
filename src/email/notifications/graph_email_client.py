"""Microsoft Graph email client for DaisyBill notifications."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Final

import requests
from msal import ConfidentialClientApplication
from requests import Response, Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.email.config.settings import EmailSettings
from src.email.notifications.email_exceptions import (
    DuplicateEmailSkipped,
    EmailAuthenticationError,
    EmailSendError,
)
from src.email.notifications.email_models import EmailMessage
from src.email.notifications.idempotency import EmailCheckpointStore
from src.email.config.logging_config import configure_logging

run_id = configure_logging()
LOGGER = logging.getLogger(__name__)
GRAPH_SEND_MAIL_PATH: Final[str] = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
HTTP_ACCEPTED: Final[int] = 202


@dataclass(slots=True)
class GraphEmailClient:
    """Sends HTML email through Microsoft Graph using app-only credentials."""

    settings: EmailSettings
    checkpoint_store: EmailCheckpointStore
    session: Session | None = None

    def send_email(self, email_message: EmailMessage, idempotency_key: str) -> None:
        """Send an email once using a deterministic idempotency key.

        Args:
            email_message: Prepared email subject, recipients, and HTML body.
            idempotency_key: Unique business key for this exact email event.

        Returns:
            None.

        Raises:
            DuplicateEmailSkipped: If the email was already sent.
            EmailAuthenticationError: If token acquisition fails.
            EmailSendError: If Microsoft Graph rejects the email.
        """
        self._validate_message(email_message, idempotency_key)
        if self.checkpoint_store.has_sent(idempotency_key):
            LOGGER.warning("Duplicate email skipped")
            raise DuplicateEmailSkipped("Email already sent for this idempotency key")

        LOGGER.info("Sending email notification")
        access_token = self._acquire_access_token()
        self._post_email(access_token, email_message)
        self.checkpoint_store.mark_sent(idempotency_key)
        LOGGER.info("Email notification sent successfully")

    def _validate_message(self, email_message: EmailMessage, idempotency_key: str) -> None:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key cannot be blank")
        if not email_message.subject.strip():
            raise ValueError("email subject cannot be blank")
        if not email_message.html_body.strip():
            raise ValueError("email body cannot be blank")
        if not email_message.to_addresses:
            raise ValueError("email requires at least one recipient")

    def _acquire_access_token(self) -> str:
        app = ConfidentialClientApplication(
            self.settings.client_id,
            authority=self.settings.authority,
            client_credential=self.settings.client_secret,
        )
        token_result = app.acquire_token_for_client(scopes=list(self.settings.scopes))
        access_token = token_result.get("access_token")
        if not access_token:
            LOGGER.error("Microsoft Graph authentication failed")
            raise EmailAuthenticationError("Microsoft Graph authentication failed")
        return str(access_token)

    @retry(
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError, EmailSendError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _post_email(self, access_token: str, email_message: EmailMessage) -> None:
        response = self._session.post(
            url=GRAPH_SEND_MAIL_PATH.format(sender=self.settings.from_address),
            headers=self._build_headers(access_token),
            data=json.dumps(self._build_payload(email_message)),
            timeout=self.settings.timeout_seconds,
        )
        self._raise_for_failed_response(response)

    @property
    def _session(self) -> Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def _build_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, email_message: EmailMessage) -> dict[str, Any]:
        return {
            "message": {
                "subject": email_message.subject,
                "body": {"contentType": "HTML", "content": email_message.html_body},
                "toRecipients": self._build_recipients(email_message.to_addresses),
                "ccRecipients": self._build_recipients(email_message.cc_addresses),
            },
            "saveToSentItems": True,
        }

    def _build_recipients(self, addresses: tuple[str, ...]) -> list[dict[str, dict[str, str]]]:
        return [{"emailAddress": {"address": address}} for address in addresses]

    def _raise_for_failed_response(self, response: Response) -> None:
        if response.status_code == HTTP_ACCEPTED:
            return
        status_code = response.status_code
        safe_response_text = response.text[:500]
        LOGGER.error("Microsoft Graph sendMail failed with status %s", status_code)
        raise EmailSendError(f"Microsoft Graph sendMail failed: {status_code} {safe_response_text}")
