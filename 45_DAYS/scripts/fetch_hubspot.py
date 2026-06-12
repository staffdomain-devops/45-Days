"""Fetch HubSpot contact data and write $RUNNER_TEMP/hubspot_contact.json."""

import os
import re
import json
import sys
import logging
from datetime import datetime, timezone, timedelta

from bs4 import BeautifulSoup
import requests
from hubspot import HubSpot
from hubspot.crm.contacts.exceptions import ApiException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fetch_hubspot")

CONTACT_PROPERTIES = [
    "firstname", "lastname", "email", "jobtitle", "company",
    "industry", "num_employees", "city", "country", "website",
    "hubspot_owner_id",
]
CHORUS_URL_REGEX = re.compile(r"chorus\.ai/meeting/([A-Za-z0-9]+)")


def strip_html(html_str):
    if not html_str:
        return ""
    return BeautifulSoup(html_str, "html.parser").get_text(separator=" ", strip=True)


def fetch_contact_properties(client, contact_id):
    result = client.crm.contacts.basic_api.get_by_id(contact_id, properties=CONTACT_PROPERTIES)
    return result.properties


def fetch_deal_stage(client, contact_id):
    try:
        assoc = client.crm.contacts.associations_api.get_all(contact_id, "deals", limit=10)
        deal_ids = [a.id for a in (assoc.results or [])]
        if not deal_ids:
            return None
        deals = []
        for deal_id in deal_ids:
            try:
                d = client.crm.deals.basic_api.get_by_id(deal_id, properties=["dealstage", "createdate"])
                deals.append(d)
            except ApiException:
                pass
        if not deals:
            return None
        deals.sort(key=lambda d: d.properties.get("createdate") or "", reverse=True)
        return deals[0].properties.get("dealstage")
    except ApiException:
        return None


def resolve_owner_first_name(client, owner_id):
    if not owner_id:
        return None
    try:
        result = client.crm.owners.owners_api.get_by_id(owner_id)
        return result.first_name
    except ApiException:
        return None


def fetch_email_engagements(contact_id, since, hubspot_key):
    url = f"https://api.hubapi.com/engagements/v1/engagements/associated/CONTACT/{contact_id}/paged"
    headers = {"Authorization": f"Bearer {hubspot_key}"}
    since_ms = int(since.timestamp() * 1000)
    engagements = []
    offset = None

    while True:
        params = {"limit": 250}
        if offset is not None:
            params["offset"] = offset
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("results", []):
            eng = item.get("engagement", {})
            if eng.get("type") != "EMAIL":
                continue
            if eng.get("timestamp", 0) < since_ms:
                continue
            meta = item.get("metadata", {})
            from_data = meta.get("from") or {}
            to_list = meta.get("to") or []
            ts_ms = eng.get("timestamp", 0)
            ts_iso = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat() if ts_ms else ""
            engagements.append({
                "id": str(eng.get("id", "")),
                "timestamp": ts_iso,
                "subject": meta.get("subject", ""),
                "from": from_data.get("email", ""),
                "to": ", ".join(t.get("email", "") for t in to_list if t.get("email")),
                "body": strip_html(meta.get("html") or meta.get("text", "")),
            })

        if not data.get("hasMore"):
            break
        offset = data.get("offset")

    return engagements


def fetch_meeting_engagements(contact_id, since, hubspot_key):
    url = f"https://api.hubapi.com/engagements/v1/engagements/associated/CONTACT/{contact_id}/paged"
    headers = {"Authorization": f"Bearer {hubspot_key}"}
    since_ms = int(since.timestamp() * 1000)
    meetings = []
    offset = None

    while True:
        params = {"limit": 250}
        if offset is not None:
            params["offset"] = offset
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("results", []):
            eng = item.get("engagement", {})
            if eng.get("type") != "MEETING":
                continue
            if eng.get("timestamp", 0) < since_ms:
                continue
            meta = item.get("metadata", {})
            ts_ms = eng.get("timestamp", 0)
            ts_iso = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat() if ts_ms else ""
            attendees_raw = meta.get("attendees") or []
            attendees = [a.get("email", "") for a in attendees_raw if a.get("email")]
            meetings.append({
                "id": str(eng.get("id", "")),
                "timestamp": ts_iso,
                "title": meta.get("title", ""),
                "notes": strip_html(meta.get("body", "")),
                "internal_notes": strip_html(meta.get("internalMeetingNotes", "")),
                "attendees": attendees,
            })

        if not data.get("hasMore"):
            break
        offset = data.get("offset")

    return meetings


def fetch_crm_meetings(client, contact_id, since, hubspot_key):
    url = f"https://api.hubapi.com/crm/v4/objects/contacts/{contact_id}/associations/meetings"
    headers = {"Authorization": f"Bearer {hubspot_key}"}
    resp = requests.get(url, headers=headers, params={"limit": 100}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    meeting_ids = [r.get("toObjectId") for r in data.get("results", []) if r.get("toObjectId")]

    meetings = []
    for meeting_id in meeting_ids:
        try:
            m = client.crm.objects.meetings.basic_api.get_by_id(
                meeting_id,
                properties=["hs_meeting_title", "hs_meeting_body", "hs_internal_meeting_notes", "hs_timestamp"],
            )
            ts_raw = m.properties.get("hs_timestamp", "")
            if ts_raw:
                try:
                    ts_dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    if ts_dt < since:
                        continue
                    ts_iso = ts_dt.isoformat()
                except ValueError:
                    ts_iso = ts_raw
            else:
                ts_iso = ""
            meetings.append({
                "id": str(meeting_id),
                "timestamp": ts_iso,
                "title": m.properties.get("hs_meeting_title", ""),
                "notes": strip_html(m.properties.get("hs_meeting_body", "")),
                "internal_notes": strip_html(m.properties.get("hs_internal_meeting_notes", "")),
            })
        except ApiException as exc:
            log.warning(f"Could not fetch CRM meeting {meeting_id}: {exc}")

    return meetings


def extract_chorus_ids(meeting_engagements, crm_meetings):
    ids = []
    all_meetings = meeting_engagements + crm_meetings
    for m in all_meetings:
        for field in ("notes", "internal_notes"):
            text = m.get(field, "") or ""
            ids.extend(CHORUS_URL_REGEX.findall(text))
    return list(dict.fromkeys(ids))


if __name__ == "__main__":
    contact_id = os.environ["INPUT_CONTACT_ID"]
    contact_email = os.environ["INPUT_CONTACT_EMAIL"]
    hubspot_key = os.environ["HUBSPOT_API_KEY"]
    runner_temp = os.environ.get("RUNNER_TEMP", ".")

    log.info(f"Fetching HubSpot data for contact {contact_id} ({contact_email})")

    client = HubSpot(access_token=hubspot_key)
    since = datetime.now(timezone.utc) - timedelta(days=365)

    contact_props = fetch_contact_properties(client, contact_id)
    deal_stage = fetch_deal_stage(client, contact_id)
    email_history = fetch_email_engagements(contact_id, since, hubspot_key)
    meeting_engagements = fetch_meeting_engagements(contact_id, since, hubspot_key)
    crm_meetings = fetch_crm_meetings(client, contact_id, since, hubspot_key)

    all_meetings = {m["id"]: m for m in meeting_engagements}
    for m in crm_meetings:
        all_meetings.setdefault(m["id"], m)
    merged_meetings = list(all_meetings.values())

    chorus_ids = extract_chorus_ids(meeting_engagements, crm_meetings)

    owner_id = contact_props.get("hubspot_owner_id")
    contact_props["hubspot_owner_first_name"] = resolve_owner_first_name(client, owner_id) or ""

    output = {
        "contact_properties": contact_props,
        "deal_stage": deal_stage,
        "email_history": email_history,
        "meeting_engagements": merged_meetings,
        "chorus_conversation_ids": chorus_ids,
    }

    out_path = os.path.join(runner_temp, "hubspot_contact.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    log.info(f"Wrote {out_path} — {len(email_history)} emails, {len(merged_meetings)} meetings, {len(chorus_ids)} Chorus IDs")
