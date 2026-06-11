from email.notifications.email_models import ExceptionDetail, RunContext, RunMetrics
from email.notifications.email_templates import build_failure_body, build_success_body


def test_success_template_contains_metrics_and_run_id() -> None:
    context = RunContext(
        run_id="run-123",
        process_name="CRH DaisyBill Automation",
        run_date="2026-04-27",
        output_links={"Output Report": "https://example.com/output"},
    )
    metrics = RunMetrics(
        total_invoices=10,
        successfully_processed=8,
        business_exceptions=1,
        system_exceptions=1,
    )

    html_body = build_success_body(context, metrics)

    assert "Completed Successfully" in html_body
    assert "80%" in html_body
    assert "run-123" in html_body
    assert "Output Report" in html_body


def test_success_template_escapes_exception_content() -> None:
    context = RunContext(run_id="run-123", process_name="CRH DaisyBill Automation", run_date="2026-04-27")
    metrics = RunMetrics(total_invoices=1, successfully_processed=0, business_exceptions=1, system_exceptions=0)
    exceptions = [ExceptionDetail(invoice_number="INV-1", category="Business", reason="<script>alert(1)</script>")]

    html_body = build_success_body(context, metrics, exceptions)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_body
    assert "<script>alert(1)</script>" not in html_body


def test_failure_template_contains_impact_counts() -> None:
    context = RunContext(run_id="run-999", process_name="CRH DaisyBill Automation", run_date="2026-04-27")

    html_body = build_failure_body(
        context=context,
        step="DaisyBill Login",
        error_summary="Timeout waiting for page",
        processed_count=3,
        remaining_count=7,
    )

    assert "Run Failed" in html_body
    assert "DaisyBill Login" in html_body
    assert "Timeout waiting for page" in html_body
    assert "run-999" in html_body
