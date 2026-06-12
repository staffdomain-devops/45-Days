"""Compute runtime campaign tokens (current date, EOFY timing context, days to EOFY) and write $RUNNER_TEMP/campaign_tokens.json."""

import os
import json
import logging
from datetime import datetime, timezone, date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("compute_campaign_tokens")


def compute_eofy_context(today: date) -> tuple:
    if today.month < 6 or (today.month == 6 and today.day <= 30):
        eofy_date = date(today.year, 6, 30)
    else:
        eofy_date = date(today.year + 1, 6, 30)

    days_to_eofy = (eofy_date - today).days

    if days_to_eofy > 45:
        timing_context = "pre_eofy_full"
    elif 0 <= days_to_eofy <= 45:
        timing_context = "pre_eofy_compressed"
    else:
        timing_context = "post_eofy"

    return timing_context, days_to_eofy


if __name__ == "__main__":
    runner_temp = os.environ.get("RUNNER_TEMP", ".")
    today = datetime.now(timezone.utc).date()
    timing_context, days = compute_eofy_context(today)

    tokens = {
        "current_date": today.isoformat(),
        "eofy_timing_context": timing_context,
        "days_to_eofy": days,
    }

    out_path = os.path.join(runner_temp, "campaign_tokens.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    log.info(f"Wrote {out_path}: current_date={tokens['current_date']}, eofy_timing_context={timing_context}, days_to_eofy={days}")
