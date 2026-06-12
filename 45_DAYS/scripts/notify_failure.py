"""Read failed_contacts.json from $RUNNER_TEMP and POST a failure notification to TEAMS_WEBHOOK_URL (PIPE-06)."""

import os
import json
import logging

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("notify_failure")

if __name__ == "__main__":
    runner_temp = os.environ.get("RUNNER_TEMP", ".")
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL", "")

    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}" if run_id else "unknown"

    dlq_path = os.path.join(runner_temp, "failed_contacts.json")
    try:
        with open(dlq_path, encoding="utf-8") as f:
            dlq = json.load(f)
    except Exception as exc:
        log.error(f"Could not read DLQ record from {dlq_path}: {exc}")
        dlq = {
            "contact_email": os.environ.get("INPUT_CONTACT_EMAIL", "unknown"),
            "failed_step": "unknown",
            "error_message": "DLQ record unavailable",
        }

    contact_email = dlq.get("contact_email", "unknown")
    failed_step = dlq.get("failed_step", "unknown")
    error_excerpt = dlq.get("error_message", "")[:300]

    message = (
        f"Campaign pipeline FAILED for {contact_email}. "
        f"Step: {failed_step}. "
        f"Error: {error_excerpt}. "
        f"Run log: {run_url}"
    )

    if not webhook_url:
        log.warning("TEAMS_WEBHOOK_URL not set — skipping notification")
    else:
        try:
            resp = requests.post(webhook_url, json={"text": message}, timeout=15)
            resp.raise_for_status()
            log.info("Failure notification sent successfully")
        except Exception as exc:
            log.error(f"Failed to send notification (non-fatal): {exc}")
