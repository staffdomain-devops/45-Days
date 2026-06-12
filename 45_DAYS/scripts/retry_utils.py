"""Shared retry configuration and DLQ utilities for the 45-Days pipeline."""

import os
import json
import logging
from datetime import datetime, timezone

from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_random_exponential,
    retry_if_exception,
)

log = logging.getLogger(__name__)


def _is_retryable(exc):
    """Return True for 429 and 5xx status codes; all other exceptions are permanent failures."""
    status = None
    if hasattr(exc, "status") and exc.status is not None:
        status = exc.status
    elif hasattr(exc, "response") and exc.response is not None:
        status = getattr(exc.response, "status_code", None)
    elif hasattr(exc, "status_code") and exc.status_code is not None:
        status = exc.status_code
    if status is None:
        return False
    return status == 429 or status >= 500


_exp_wait = wait_random_exponential(multiplier=1, min=1, max=60)


def _combined_wait(retry_state):
    """Exponential backoff, floored by Retry-After header when present."""
    exp = _exp_wait(retry_state)
    exc = retry_state.outcome.exception()
    retry_after = 0.0
    if exc and hasattr(exc, "response") and exc.response is not None:
        header = exc.response.headers.get("Retry-After")
        if header:
            try:
                retry_after = float(header)
            except ValueError:
                pass
    return max(exp, retry_after)


RETRY_KWARGS = dict(
    retry=retry_if_exception(_is_retryable),
    wait=_combined_wait,
    stop=stop_after_attempt(6) | stop_after_delay(60),
    reraise=True,
)


def write_dlq(contact_id, contact_email, failed_step, error_message, retry_count=0):
    """Write a DLQ record to $RUNNER_TEMP/failed_contacts.json (ERR-04)."""
    record = {
        "contact_id": contact_id,
        "contact_email": contact_email,
        "failed_step": failed_step,
        "error_message": str(error_message)[:2000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": retry_count,
    }
    path = os.path.join(os.environ.get("RUNNER_TEMP", "."), "failed_contacts.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        log.info(f"DLQ record written to {path}")
    except Exception as dlq_exc:
        log.error(f"Failed to write DLQ record: {dlq_exc}")
