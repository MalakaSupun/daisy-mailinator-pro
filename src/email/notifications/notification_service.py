"""High-level DaisyBill notification service."""

from __future__ import annotations
import sys
import html
from typing import Sequence
from dataclasses import dataclass

from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.email.config.settings import EmailSettings
from src.email.notifications.email_models import EmailMessage, ExceptionDetail, RunContext, RunMetrics
from src.email.notifications.email_templates import (
    build_exception_alert_body,
    build_failure_body,
    build_no_data_body,
    build_success_body,
)
from src.email.notifications.graph_email_client import GraphEmailClient
from src.email.config.logging_config import configure_logging

run_id = configure_logging()


@dataclass(frozen=True, slots=True)
class EmailNotificationService:
    """Creates and sends standardized DaisyBill automation emails."""

    settings: EmailSettings
    email_client: GraphEmailClient

    def send_success(self, 
        subject_success: str, 
        processed_date: str, 
        context: RunContext, 
        metrics: RunMetrics, 
        exceptions: Sequence[ExceptionDetail] = (), 
        additional_info: str = "") -> None:
        """Send completed-run summary email.

        Args:
            subject_success: The subject line for the success email.
            processed_date: The date when the process was processed.
            context: Common run metadata.
            metrics: Run processing metrics.
            exceptions: Optional summarized exceptions.
            additional_info: Additional information to include in the email.

        Returns:
            None.

        Raises:
            EmailNotificationError: If the email cannot be sent.
        """
        # CRH DaisyBill - Process Completed for {state} | {processed_date}
        message = self._build_message(subject_success, build_success_body(context, metrics, exceptions, additional_info))
        
        readable_html = html.unescape(message.html_body)
        # print(readable_html)

        self.email_client.send_email(message, self._key(context.run_id, "success"))

    def send_no_data(self, context: RunContext) -> None:
        """Send no-data notification email.

        Args:
            context: Common run metadata.

        Returns:
            None.

        Raises:
            EmailNotificationError: If the email cannot be sent.
        """
        message = self._build_message("CRH DaisyBill - No Data Available", build_no_data_body(context))
        self.email_client.send_email(message, self._key(context.run_id, "no-data"))

    def send_failure(self, context: RunContext, step: str, error_summary: str, processed_count: int, remaining_count: int) -> None:
        """Send fatal failure email.

        Args:
            context: Common run metadata.
            step: Automation step where the failure occurred.
            error_summary: Sanitized error summary safe for email recipients.
            processed_count: Number of invoices completed before failure.
            remaining_count: Number of invoices not processed.

        Returns:
            None.

        Raises:
            EmailNotificationError: If the email cannot be sent.
        """
        body = build_failure_body(context, step, error_summary, processed_count, remaining_count)
        message = self._build_message("[CRH DaisyBill] Process Failed", body)
        self.email_client.send_email(message, self._key(context.run_id, "failure"))

    def send_exception_alert(self, context: RunContext, exceptions: Sequence[ExceptionDetail]) -> None:
        """Send exception alert email.

        Args:
            context: Common run metadata.
            exceptions: Exceptions requiring manual review.

        Returns:
            None.

        Raises:
            ValueError: If no exceptions are provided.
            EmailNotificationError: If the email cannot be sent.
        """
        if not exceptions:
            raise ValueError("exception alert requires at least one exception")
        message = self._build_message("CRH DaisyBill - Exception Alert", build_exception_alert_body(context, exceptions))
        print(message)
        # self.email_client.send_email(message, self._key(context.run_id, "exception-alert"))

    def _build_message(self, subject: str, html_body: str) -> EmailMessage:
        return EmailMessage(
            subject=subject,
            html_body=html_body,
            to_addresses=self.settings.to_addresses,
            cc_addresses=self.settings.cc_addresses,
        )

    def _key(self, run_id: str, email_type: str) -> str:
        return f"crh-daisybill:{run_id}:{email_type}"
