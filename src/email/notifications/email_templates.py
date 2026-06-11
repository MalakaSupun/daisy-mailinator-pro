"""HTML templates for CRH DaisyBill automation notification emails."""

from __future__ import annotations

import html
from collections.abc import Sequence
from typing import Final

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.email.notifications.email_models import ExceptionDetail, RunContext, RunMetrics
from src.email.config.logging_config import configure_logging

run_id = configure_logging()

PROCESS_NAME: Final[str] = "CRH DaisyBill Automation"
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

def build_success_body(
    context: RunContext,
    metrics: RunMetrics,
    exceptions: Sequence[ExceptionDetail] = (),
    additional_info: str = "",
    ) -> str:
    """Build the successful run summary email body.

    Args:
        context: Common run metadata.
        metrics: Run-level processing metrics.
        exceptions: Optional summarized exceptions encountered during the run.
        additional_info: Additional information to include in the email.

    Returns:
        HTML email body.

    Raises:
        None.
    """
    return _page(
        title=f"{context.process_name} - Completed Successfully",
        body_sections=(
            _paragraph(f"Hello Team,<br><br>The {context.process_name} has been executed successfully on {html.escape(context.run_date)}."),
            _metrics_table(metrics),
            _highlights_section(),
            _links_section(context.output_links),
            _exceptions_section(exceptions),
            _run_id_section(context.run_id),
            _paragraph(additional_info),
        ),
    )


def build_no_data_body(context: RunContext) -> str:
    """Build the no-data notification email body.

    Args:
        context: Common run metadata.

    Returns:
        HTML email body.

    Raises:
        None.
    """
    return _page(
        title=f"{context.process_name} - No Data Available",
        body_sections=(
            _paragraph(f"Hello Team,<br><br>The {context.process_name} completed successfully."),
            _paragraph("No invoices were available for processing today."),
            _links_section(context.output_links),
            _run_id_section(context.run_id),
        ),
    )


def build_failure_body(context: RunContext, step: str, error_summary: str, processed_count: int, remaining_count: int) -> str:
    """Build the fatal failure notification email body.

    Args:
        context: Common run metadata.
        step: Automation step where the failure occurred.
        error_summary: Sanitized error summary safe for email recipients.
        processed_count: Number of invoices completed before failure.
        remaining_count: Number of invoices not processed.

    Returns:
        HTML email body.

    Raises:
        None.
    """
    rows = {
        "Step": step,
        "Error": error_summary,
        "Processed Before Failure": str(processed_count),
        "Remaining": str(remaining_count),
    }
    return _page(
        title=f"{context.process_name} - Run Failed",
        body_sections=(
            _paragraph(f"Hello Team,<br><br>The {context.process_name} encountered a failure during execution."),
            _key_value_table(rows),
            _paragraph("Immediate attention is required. Please review the logs before restarting the process."),
            _links_section(context.output_links),
            _run_id_section(context.run_id),
        ),
    )


def build_exception_alert_body(context: RunContext, exceptions: Sequence[ExceptionDetail]) -> str:
    """Build the business/system exception alert email body.

    Args:
        context: Common run metadata.
        exceptions: Summarized exceptions requiring review.

    Returns:
        HTML email body.

    Raises:
        None.
    """
    return _page(
        title=f"{context.process_name} - Exception Alert",
        body_sections=(
            _paragraph(f"Hello Team,<br><br>The {context.process_name} encountered exceptions requiring review."),
            _exceptions_section(exceptions),
            _links_section(context.output_links),
            _run_id_section(context.run_id),
        ),
    )


def _page(title: str, body_sections: Sequence[str]) -> str:
    joined_sections = "\n".join(section for section in body_sections if section)
    #        <h2 style="color:#007b7f;">{html.escape(PROCESS_NAME)} - {html.escape(title)}</h2>
    return f"""
    <html>
      <body style="font-family:Arial, sans-serif; font-size:13px; color:#222;">
        <h2 style="color:#007b7f;">{title}</h2>
        {joined_sections}
        {_footer()}
      </body>
    </html>
    """


def _paragraph(content: str) -> str:
    return f"<p>{content}</p>"


def _metrics_table(metrics: RunMetrics) -> str:
    rows = {
        "Total Invoices": str(metrics.total_invoices),
        "Successfully Processed": str(metrics.successfully_processed),
        "Business Exceptions": str(metrics.business_exceptions),
        "System Exceptions": str(metrics.system_exceptions),
        "Success Rate": metrics.success_rate,
    }
    return _key_value_table(rows)


def _key_value_table(rows: dict[str, str]) -> str:
    table_rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>" for label, value in rows.items()
    )
    return f"""
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; min-width:420px;">
      {table_rows}
    </table>
    """


def _highlights_section() -> str:
    return """
    <p><strong>Key Highlights:</strong></p>
    <ul>
      <li>Invoices were validated and submitted to DaisyBill where eligible.</li>
      <li>Experity notes were added for completed invoices.</li>
      <li>Processed files were moved according to their final status.</li>
    </ul>
    """


def _links_section(output_links: dict[str, str] | object) -> str:
    if not output_links:
        return ""
    items = "".join(
        f'<li><a href="{html.escape(url)}">{html.escape(label)}</a></li>' for label, url in dict(output_links).items()
    )
    return f"<p><strong>Output Links:</strong></p><ul>{items}</ul>"


def _exceptions_section(exceptions: Sequence[ExceptionDetail]) -> str:
    if not exceptions:
        return ""
    rows = "".join(_exception_row(exception) for exception in exceptions[:25])
    notice = "<p>Only the first 25 exceptions are shown. Review the exception report for full details.</p>"
    return f"""
    <p><strong>Exception Summary:</strong></p>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; min-width:640px;">
      <tr style="background-color:#f2f2f2;"><th>Invoice</th><th>Category</th><th>Reason</th></tr>
      {rows}
    </table>
    {notice if len(exceptions) > 25 else ""}
    """


def _exception_row(exception: ExceptionDetail) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(exception.invoice_number)}</td>"
        f"<td>{html.escape(exception.category)}</td>"
        f"<td>{html.escape(exception.reason)}</td>"
        "</tr>"
    )


def _run_id_section(run_id: str) -> str:
    return f"<p><strong>Run ID:</strong> {html.escape(run_id)}</p>"


def _footer() -> str:
   return """
    <div style="
        font-family: Arial, sans-serif;
        font-size: 13px;
        color: inherit;
        line-height: 1.5;
    ">

        <p style="margin: 0 0 12px 0;">
            Best Regards,
        </p>

        <p style="
            margin: 0;
            color: #1DB5B0;
            font-weight: bold;
        ">
            Innobot Health
        </p>

        <p style="
            margin: 0 0 12px 0;
            font-weight: bold;
            color: #FFFFFF;
        ">
            ROBOTIC PROCESS AUTOMATION DEPARTMENT
        </p>

        <p style="margin: 0;">
            1507 NW 34th Ave | Cape Coral, FL 33993.
        </p>

        <p style="margin: 0;">
            Office: (888) 341-1009
        </p>

        <p style="margin: 0 0 14px 0;">
            Website:
            <a
                href="https://www.innobothealth.com"
                style="
                    color: #C586FF;
                    text-decoration: none;
                "
            >
                www.innobothealth.com
            </a>
        </p>

        <p style="
            margin: 0;
            font-size: 12px;
            color: #D0D0D0;
            text-align: justify;
        ">
            <strong>NOTICE:</strong>
            This email may contain PRIVILEGED and CONFIDENTIAL information and is intended
            only for the use of the specific individual(s) to which it is addressed.
            If you are not the intended recipient of this email, you are hereby notified
            that any unauthorized use, dissemination or copying of this email or the
            information contained in it or attached to it is strictly prohibited.
            You may be subject to penalties under law for any improper use or further
            disclosure of any Protected Health Information in this email.
            If you have received this email in error, please delete it and immediately
            notify the sender of this email by reply mail. Thank you.
        </p>

    </div>
    """
    

def extra_footer() -> str:
    """
    <br>
    <p>Best Regards,<br>
    <span style="color:#007b7f;"><strong>Innobot Health</strong></span><br>
    <span style="color:#007b7f;"><strong>ROBOTIC PROCESS AUTOMATION DEPARTMENT</strong></span></p>
    <p style="font-size:11px; color:#777;">
      This is an RPA system generated email. Please do not reply to this email.<br>
      <em>Confidentiality Notice:</em> This electronic message is intended only for the named recipient and may contain confidential or privileged information.
    </p>
    """


# def build_exception_details(exception_json: dict[str, Any]) -> tuple[ExceptionDetail, ...]:
#     """Convert exception JSON into email-safe exception details.

#     Args:
#         exception_json: Exception summary JSON from the automation run.

#     Returns:
#         Flattened exception details for email rendering.

#     Raises:
#         TypeError: If exception_json is not a dictionary.
#     """
#     if not isinstance(exception_json, dict):
#         raise TypeError("exception_json must be a dictionary")

#     details: list[ExceptionDetail] = []

#     details.extend(
#         _extract_grouped_items(
#             grouped_items=exception_json.get("business", {}),
#             category_labels=BUSINESS_EXCEPTION_LABELS,
#         )
#     )

#     details.extend(
#         _extract_grouped_items(
#             grouped_items=exception_json.get("warnings", {}),
#             category_labels=WARNING_LABELS,
#         )
#     )

#     return tuple(details)


# def _extract_grouped_items(

#     grouped_items: object,
#     category_labels: dict[str, str],
#     ) -> list[ExceptionDetail]:
#     if not isinstance(grouped_items, dict):
#         return []

#     details: list[ExceptionDetail] = []

#     for raw_category, items in grouped_items.items():
#         if not isinstance(items, list):
#             continue

#         category = category_labels.get(raw_category, raw_category.replace("_", " ").title())

#         for item in items:
#             if not isinstance(item, dict):
#                 continue

#             details.append(
#                 ExceptionDetail(
#                     invoice_number=str(item.get("invoice_number", "")).strip(),
#                     category=category,
#                     reason=str(item.get("reason", "")).strip(),
#                 )
#             )

#     return details

