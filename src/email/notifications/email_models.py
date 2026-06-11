"""Data models for DaisyBill email notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class EmailType(StrEnum):
    """Supported DaisyBill notification types."""

    SUCCESS = "SUCCESS"
    NO_DATA = "NO_DATA"
    FAILURE = "FAILURE"
    EXCEPTION_ALERT = "EXCEPTION_ALERT"


@dataclass(frozen=True, slots=True)
class RunMetrics:
    """Aggregated metrics for a DaisyBill automation run."""

    total_invoices: int
    successfully_processed: int
    business_exceptions: int
    system_exceptions: int

    @property
    def success_rate(self) -> str:
        """Return the run success rate as a whole-number percentage.

        Args:
            None.

        Returns:
            Success percentage formatted for email display.

        Raises:
            None.
        """
        if self.total_invoices <= 0:
            return "0%"
        percentage = round((self.successfully_processed / self.total_invoices) * 100)
        return f"{percentage}%"


@dataclass(frozen=True, slots=True)
class ExceptionDetail:
    """A sanitized exception item suitable for email display."""

    invoice_number: str
    category: str
    reason: str


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """Prepared email payload."""

    subject: str
    html_body: str
    to_addresses: tuple[str, ...]
    cc_addresses: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RunContext:
    """Common context included in all DaisyBill notification templates."""

    run_id: str
    process_name: str
    run_date: str
    output_links: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BusinessExceptionCategories:
    """Supported business exception categories for DaisyBill automation."""
    EXTRACTION_ERROR = "Extraction Error"
    VALIDATION_ERROR = "Validation Error"
    BILLING_ERROR = "Billing Error"
    INJURY_ERROR = "Injury Error"
    OTHER_ERROR = "Other Error"


@dataclass(frozen=True, slots=True)
class WarningExceptionCategories:
    """Supported warning exception categories for DaisyBill automation."""
    
    No_TABLE_LINES = "No red pointers detected on the invoice"


class BusinessException_info(BusinessExceptionCategories):
    """Structured information for a business exception."""
    # description: str
    # error_type: str
    # invoice_number: str
    tuple[ExceptionDetail, ...]

    # @property
    # def error_summary(self) -> str:
    #     """Generate a concise error summary for email display."""
    #     if self.error_type and self.description:
    #         return f"{self.invoice_number} : {self.error_type}|{self.description}"
