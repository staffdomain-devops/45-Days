"""Fetch Chorus AI call transcripts and write $RUNNER_TEMP/chorus_transcripts.json (CHO-01..CHO-04)."""

import os
import json
import logging

import requests
from tenacity import retry, stop_after_attempt, retry_if_exception

from retry_utils import _is_retryable, _combined_wait

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fetch_chorus")

CHORUS_API_V1 = "https://chorus.ai/api/v1"
CHORUS_API_V3 = "https://chorus.ai/api/v3"
TRANSCRIPT_TIMEOUT = 30

_CHORUS_RETRY_KWARGS = dict(
    retry=retry_if_exception(_is_retryable),
    wait=_combined_wait,
    stop=stop_after_attempt(3),
    reraise=True,
)


def _auth_header(api_token):
    return {"Authorization": f"Token {api_token}"}


@retry(**_CHORUS_RETRY_KWARGS)
def _fetch_transcript_raw(conversation_id, api_token):
    """Inner HTTP call with retry for 429/5xx only. Raises on retryable errors."""
    url = f"{CHORUS_API_V1}/conversations/{conversation_id}?fields=recording.utterances"
    resp = requests.get(url, headers=_auth_header(api_token), timeout=TRANSCRIPT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_transcript(conversation_id, api_token):
    """Fetch utterances for a single conversation. Silently returns None on 404/401/timeout (CHO-03)."""
    try:
        data = _fetch_transcript_raw(conversation_id, api_token)
        return {
            "conversation_id": conversation_id,
            "utterances": data.get("recording", {}).get("utterances", []),
        }
    except requests.exceptions.Timeout:
        log.warning(f"Chorus: timeout fetching conversation {conversation_id} — silent fallback")
        return None
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (401, 404):
            log.warning(f"Chorus: conversation {conversation_id} returned {status} — silent fallback")
            return None
        log.warning(f"Chorus: HTTP {status} for conversation {conversation_id} after retries — silent fallback")
        return None
    except Exception as exc:
        log.warning(f"Chorus: unexpected error for conversation {conversation_id}: {exc} — silent fallback")
        return None


def search_chorus_by_company(company_name, api_token):
    """Search Chorus v3 engagements by company name. Returns list of conversation IDs (CHO-01 source 3)."""
    if not company_name:
        return []
    try:
        resp = requests.get(
            f"{CHORUS_API_V3}/engagements",
            headers=_auth_header(api_token),
            params={"account_name": company_name, "limit": 10},
            timeout=TRANSCRIPT_TIMEOUT,
        )
        if resp.status_code in (401, 404):
            log.warning(f"Chorus: company search returned {resp.status_code} — skipping")
            return []
        resp.raise_for_status()
        data = resp.json()
        engagements = data.get("engagements", data.get("data", []))
        ids = []
        for e in engagements:
            cid = e.get("conversation_id") or e.get("id")
            if cid:
                ids.append(str(cid))
        return ids
    except Exception as exc:
        log.warning(f"Chorus: company search error: {exc} — skipping")
        return []


if __name__ == "__main__":
    runner_temp = os.environ.get("RUNNER_TEMP", ".")
    chorus_token = os.environ.get("CHORUS_API_TOKEN", "")
    input_chorus_ids = os.environ.get("INPUT_CHORUS_IDS", "")

    hubspot_path = os.path.join(runner_temp, "hubspot_contact.json")

    # Source 1: IDs extracted by fetch_hubspot.py from HubSpot meeting notes
    hubspot_ids = []
    company_name = ""
    try:
        with open(hubspot_path, encoding="utf-8") as f:
            hubspot_data = json.load(f)
        hubspot_ids = hubspot_data.get("chorus_conversation_ids", [])
        company_name = (hubspot_data.get("contact_properties") or {}).get("company", "")
    except Exception as exc:
        log.warning(f"Could not read hubspot_contact.json for Chorus IDs: {exc}")

    # Source 2: Manual override via INPUT_CHORUS_IDS env var (CHO-01)
    override_ids = [cid.strip() for cid in input_chorus_ids.split(",") if cid.strip()] if input_chorus_ids else []

    # Source 3: Chorus v3 search by company name (CHO-01)
    search_ids = []
    if chorus_token and company_name:
        search_ids = search_chorus_by_company(company_name, chorus_token)

    all_ids = list(dict.fromkeys(hubspot_ids + override_ids + search_ids))
    log.info(
        f"Chorus IDs to fetch: {len(all_ids)} total "
        f"({len(hubspot_ids)} from HubSpot, {len(override_ids)} override, {len(search_ids)} from search)"
    )

    transcripts = []
    if not chorus_token:
        log.warning("CHORUS_API_TOKEN not set — skipping Chorus transcript fetch (silent fallback per CHO-03)")
    else:
        for cid in all_ids:
            result = fetch_transcript(cid, chorus_token)
            if result is not None:
                transcripts.append(result)

    out_path = os.path.join(runner_temp, "chorus_transcripts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(transcripts, f, indent=2)
    log.info(f"Wrote {out_path}: {len(transcripts)} transcripts from {len(all_ids)} IDs")
