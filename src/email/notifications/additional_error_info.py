"""HTML templates for DaisyBill email notifications."""

from __future__ import annotations

from collections import defaultdict
from html import escape
from typing import Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.email.notifications.email_models import ExceptionDetail

BUSINESS_EXCEPTION_LABELS: dict[str, str] = {
    "EXTRACTION_ERROR": "Extraction Error",
    "VALIDATION_ERROR": "Validation Error",
    "BILLING_ERROR": "Billing Error",
    "INJURY_ERROR": "Injury Error",
    "OTHER_ERROR": "Other Error",
}

WARNING_LABELS: dict[str, str] = {
    "NO_RED_PART": "No Red Part Warning",
    "OTHER": "Other Warning",
}


def render_business_exception_section(
    exceptions: tuple[ExceptionDetail, ...],
    max_items_per_category: int = 10,
    ) -> str:
    """Render grouped business exceptions as an HTML email section.

    Args:
        exceptions: Sanitized exception details to include in the email.
        max_items_per_category: Maximum visible rows per exception category.

    Returns:
        HTML section for grouped business exceptions.

    Raises:
        ValueError: If max_items_per_category is less than one.
    """
    if max_items_per_category < 1:
        raise ValueError("max_items_per_category must be greater than zero")

    if not exceptions:
        return ""

    grouped_exceptions = _group_exceptions_by_category(exceptions)
    category_blocks = _render_exception_category_blocks(
        grouped_exceptions=grouped_exceptions,
        max_items_per_category=max_items_per_category,
    )

    return f"""
    <hr style="border:0; border-top:1px solid #d9d9d9; margin:24px 0;">

    <div style="font-family:Arial, sans-serif; font-size:14px; color:#222222;">
        <p style="margin:0 0 12px 0;">
            For this run, we found the following issues in the scenarios below:
        </p>

        {category_blocks}
    </div>
    <hr style="border:0; border-top:1px solid #d9d9d9; margin:24px 0;">
    """


def _group_exceptions_by_category(
    exceptions: tuple[ExceptionDetail, ...],
    ) -> dict[str, list[ExceptionDetail]]:
    grouped_exceptions: dict[str, list[ExceptionDetail]] = defaultdict(list)

    for exception_detail in exceptions:
        grouped_exceptions[exception_detail.category].append(exception_detail)

    return dict(grouped_exceptions)


def _render_exception_category_blocks(
    grouped_exceptions: dict[str, list[ExceptionDetail]],
    max_items_per_category: int,
    ) -> str:
    rendered_blocks: list[str] = []

    for index, category in enumerate(sorted(grouped_exceptions), start=1):
        category_exceptions = grouped_exceptions[category]
        visible_exceptions = category_exceptions[:max_items_per_category]
        hidden_count = len(category_exceptions) - len(visible_exceptions)

        rendered_items = "".join(
            _render_exception_item(exception_detail)
            for exception_detail in visible_exceptions
        )

        more_text = _render_more_items_text(hidden_count)

        rendered_blocks.append(
            f"""
            <div style="margin:0 0 16px 0;">
                <p style="margin:0 0 6px 0; font-weight:bold;color: #1DB5B0;
            font-weight: bold;">
                    {index}. {escape(category)}:
                </p>

                <div style="margin-left:20px;">
                <ul style="margin:0; padding-left:16px;">
                    {rendered_items}
                    {more_text}
                </ul>
                </div>
            </div>
            """
        )

    return "".join(rendered_blocks)


def _render_exception_item(exception_detail: ExceptionDetail) -> str:
    invoice_number = escape(exception_detail.invoice_number)
    reason = escape(exception_detail.reason)

    return f"""
    <p style="margin:0 0 4px 0;">
        <strong>{invoice_number}:</strong> {reason}
    </p>
    """

def _render_more_items_text(hidden_count: int) -> str:
    if hidden_count <= 0:
        return ""

    return f"""
    <p style="margin:6px 0 0 0; color:#666666; font-style:italic;">
        + {hidden_count} more item(s). Please review the exception report for full details.
    </p>
    """

def build_exception_details(exception_json: dict[str, Any]) -> tuple[ExceptionDetail, ...]:
    """Convert exception JSON into email-safe exception details.

    Args:
        exception_json: Exception summary JSON from the automation run.

    Returns:
        Flattened exception details for email rendering.

    Raises:
        TypeError: If exception_json is not a dictionary.
    """
    if not isinstance(exception_json, dict):
        raise TypeError("exception_json must be a dictionary")

    details: list[ExceptionDetail] = []

    details.extend(
        _extract_grouped_items(
            grouped_items=exception_json.get("business", {}),
            category_labels=BUSINESS_EXCEPTION_LABELS,
        )
    )

    details.extend(
        _extract_grouped_items(
            grouped_items=exception_json.get("warnings", {}),
            category_labels=WARNING_LABELS,
        )
    )

    return tuple(details)


def _extract_grouped_items(
    grouped_items: object,
    category_labels: dict[str, str],
    ) -> list[ExceptionDetail]:
    if not isinstance(grouped_items, dict):
        return []

    details: list[ExceptionDetail] = []

    for raw_category, items in grouped_items.items():
        if not isinstance(items, list):
            continue

        category = category_labels.get(raw_category, raw_category.replace("_", " ").title())

        for item in items:
            if not isinstance(item, dict):
                continue

            details.append(
                ExceptionDetail(
                    invoice_number=str(item.get("invoice_number", "")).strip(),
                    category=category,
                    reason=str(item.get("reason", "")).strip(),
                )
            )

    return details


if __name__ == "__main__":
    exception_json = r"C:\Innobot_Projects\crh_healthcare_daisy_bill_process\Output\exception_summary.json"
    exception_details = build_exception_details(exception_json)

    exception_section = render_business_exception_section(
        exceptions=exception_details,
    )                                                  
    return_txt = f"""
                <html>
                <body>
                    ...
                    {exception_section}
                    {_footer()}
                </body>
                </html>
                """                                                   
    # print(return_txt)
