from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from email.config.settings import EmailSettings
from email.notifications.email_exceptions import DuplicateEmailSkipped, EmailSendError
from email.notifications.email_models import EmailMessage
from email.notifications.graph_email_client import GraphEmailClient
from email.notifications.idempotency import EmailCheckpointStore


def _settings(tmp_path: Path) -> EmailSettings:
    return EmailSettings(
        from_address="noreply-rpa1@innobothealth.com",
        to_addresses=("ops@example.com",),
        cc_addresses=(),
        client_id="client-id",
        tenant_id="tenant-id",
        client_secret="secret",
        authority="https://login.microsoftonline.com/tenant-id",
        scopes=("https://graph.microsoft.com/.default",),
        timeout_seconds=30,
        checkpoint_path=tmp_path / "checkpoint.json",
    )


def _message() -> EmailMessage:
    return EmailMessage(
        subject="[CRH DaisyBill] Completed",
        html_body="<html><body>Done</body></html>",
        to_addresses=("ops@example.com",),
    )


@patch("email.notifications.graph_email_client.ConfidentialClientApplication")
def test_send_email_posts_graph_payload(mock_app_class, tmp_path) -> None:
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "token"}
    mock_app_class.return_value = mock_app
    mock_session = MagicMock()
    mock_response = MagicMock(status_code=202, text="")
    mock_session.post.return_value = mock_response
    client = GraphEmailClient(_settings(tmp_path), EmailCheckpointStore(tmp_path / "checkpoint.json"), mock_session)

    client.send_email(_message(), "run-1:success")

    assert mock_session.post.call_count == 1
    assert (tmp_path / "checkpoint.json").exists()


@patch("email.notifications.graph_email_client.ConfidentialClientApplication")
def test_send_email_skips_duplicate(mock_app_class, tmp_path) -> None:
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "token"}
    mock_app_class.return_value = mock_app
    checkpoint_store = EmailCheckpointStore(tmp_path / "checkpoint.json")
    checkpoint_store.mark_sent("run-1:success")
    client = GraphEmailClient(_settings(tmp_path), checkpoint_store, MagicMock())

    with pytest.raises(DuplicateEmailSkipped):
        client.send_email(_message(), "run-1:success")


@patch("email.notifications.graph_email_client.ConfidentialClientApplication")
def test_send_email_raises_on_graph_failure(mock_app_class, tmp_path) -> None:
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "token"}
    mock_app_class.return_value = mock_app
    mock_session = MagicMock()
    mock_response = MagicMock(status_code=500, text="server error")
    mock_session.post.return_value = mock_response
    client = GraphEmailClient(_settings(tmp_path), EmailCheckpointStore(tmp_path / "checkpoint.json"), mock_session)

    with pytest.raises(EmailSendError):
        client.send_email(_message(), "run-2:failure")


@patch("email.notifications.graph_email_client.ConfidentialClientApplication")
def test_send_email_retries_timeout(mock_app_class, tmp_path) -> None:
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "token"}
    mock_app_class.return_value = mock_app
    mock_session = MagicMock()
    success_response = MagicMock(status_code=202, text="")
    mock_session.post.side_effect = [requests.Timeout("timeout"), success_response]
    client = GraphEmailClient(_settings(tmp_path), EmailCheckpointStore(tmp_path / "checkpoint.json"), mock_session)

    client.send_email(_message(), "run-3:success")

    assert mock_session.post.call_count == 2
