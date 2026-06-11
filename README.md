# CRH DaisyBill Email Notification Module

Production-ready Microsoft Graph email notification module for the CRH DaisyBill RPA automation.

## Purpose

This module sends standardized HTML notification emails for:

- Completed DaisyBill automation runs
- No-data runs
- Fatal automation failures
- Business/system exception alerts

It uses Microsoft Graph app-only authentication through MSAL and protects against duplicate sends using an idempotency checkpoint file.

## Minimum Python Version

Python 3.11 or later.

## Folder Layout

```text
src/        Application source code
tests/      Pytest test suite
config/     Runtime configuration files if needed
input/      Input working directory
output/     Output/checkpoint working directory
docs/       Supporting documentation
```

## Installation

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment Variables

Create `.env` from `.env.example` and set real values:

```env
EMAIL_FROM_ADDRESS=noreply-rpa1@innobothealth.com
EMAIL_TO_ADDRESSES=operations@example.com
EMAIL_CC_ADDRESSES=
EMAIL_CHECKPOINT_PATH=output/email_checkpoint.json
MS_GRAPH_CLIENT_ID=...
MS_GRAPH_TENANT_ID=...
MS_GRAPH_CLIENT_SECRET=...
MS_GRAPH_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
MS_GRAPH_SCOPE=https://graph.microsoft.com/.default
MS_GRAPH_TIMEOUT_SECONDS=30
```

Never commit `.env`.

## Example Usage

```python
from datetime import date

from email.config.logging_config import configure_logging
from email.notifications.email_models import RunContext, RunMetrics
from email.notifications.factory import build_notification_service

run_id = configure_logging()
service = build_notification_service()

context = RunContext(
    run_id=run_id,
    process_name="CRH DaisyBill Automation",
    run_date=date.today().isoformat(),
    output_links={
        "Output Report": "https://sharepoint.example/output-report.xlsx",
        "Log File": "https://sharepoint.example/run-log.txt",
    },
)

metrics = RunMetrics(
    total_invoices=10,
    successfully_processed=8,
    business_exceptions=1,
    system_exceptions=1,
)

service.send_success(context, metrics)
```

## Testing

```bash
pytest --cov=src --cov-report=term-missing
```

## Operational Notes

- Logs include a unique run ID for end-to-end traceability.
- Sensitive data such as email addresses and long numeric identifiers are redacted from logs.
- Duplicate email sends are prevented by `EMAIL_CHECKPOINT_PATH`.
- Microsoft Graph retries are limited to transient network and send failures.
- Email body content should only include information approved for recipients.

## Known Issues

- This module does not upload attachments. Use links to SharePoint/OneDrive output files instead.
- The checkpoint file should be stored on durable storage in production so restarts do not lose send history.
