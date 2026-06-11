"""Manual runner for sending a DaisyBill success email."""

from __future__ import annotations

import logging
import json
from datetime import datetime
from uuid import uuid4

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.email.notifications.graph_email_client import GraphEmailClient
from src.email.notifications.email_models import RunContext, RunMetrics
from src.email.config.logging_config import configure_logging
from src.email.notifications.notification_service import EmailNotificationService
from src.email.notifications.graph_email_client import GraphEmailClient
from src.email.notifications.idempotency import EmailCheckpointStore
from src.email.config.settings import load_email_settings
from src.email.notifications.additional_error_info import build_exception_details, render_business_exception_section

def main() -> None:
    """Send a test success email.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If email sending fails.
    """
    run_id = str(uuid4())
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | run_id=%(run_id)s | %(name)s | %(message)s",
    )

    logger = logging.LoggerAdapter(
        logging.getLogger(__name__),
        {"run_id": run_id},
    )

    logger.info("Starting manual success email runner")
    PROCESS_NAME = "CRH DaisyBill Automation - GA"


    settings = load_email_settings()

    checkpoint_store = EmailCheckpointStore(checkpoint_path=settings.checkpoint_path,)

    email_client = GraphEmailClient(
        settings=settings,
        checkpoint_store=checkpoint_store,
    )

    service = EmailNotificationService(
        settings=settings,
        email_client=email_client,
    )

    run_context = RunContext(
        run_id=run_id,
        process_name= PROCESS_NAME,
        run_date=datetime.now().strftime("%Y-%m-%d"),
        output_links={
            "Processed Output": "https://crhhealthcare-my.sharepoint.com/:x:/p/dev1_innobotrpa/IQDD3CcqoQqZS4NgRPZQBDaKAbJ9GlXa6zLL_-SaSCKuXX0?e=8TyZPV",

        },
    )

    exception_json = r"C:\Innobot_Projects\CRH_Input_Output\GA\2026_06_11\CRH_GA_2026_06_11.json"
    with open(exception_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    if  data["warnings"] or data["business"]:  
        exception_details = build_exception_details(data)
        exception_section = render_business_exception_section(
            exceptions=exception_details,
        )
    else:
        exception_section = ""

    if data["metrics"]:
        metrics = RunMetrics(
            total_invoices=data["metrics"].get("total_invoices", 0),
            successfully_processed=data["metrics"].get("successfully_processed", 0),
            business_exceptions=data["metrics"].get("business_exceptions", 0),
            system_exceptions=data["metrics"].get("system_exceptions", 0),
        ) 

    else:
        raise RuntimeError("Metrics data is missing from the exception summary JSON.")

    current_state = PROCESS_NAME
    processed_date = datetime.now().strftime("%d-%m-%Y")
    subject_success = f"CRH DaisyBill - Process Completed for {current_state} | {processed_date}"

    try:
        service.send_success(subject_success=subject_success, processed_date=processed_date, context=run_context, metrics=metrics, additional_info=exception_section)
        logger.info("Manual success email runner completed")
    except ConnectionError as e:
        logger.error(f"Failed to send success email | connection error.")
    except RuntimeError as e:
        logger.error(f"Failed to send success email | runtime error: {e}")    
    except Exception as e:
        logger.exception(f"Unexpected error in success email runner: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()