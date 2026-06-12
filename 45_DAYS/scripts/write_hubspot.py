"""Read $RUNNER_TEMP/campaign_output.json and write the campaign content back to the HubSpot contact (properties + note engagement)."""

import os
import json
import logging
import html
from datetime import datetime, timezone, date

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput
from hubspot.crm.contacts.exceptions import ApiException
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("write_hubspot")

SUBJECT_PROPS = [f"subject_{i}" for i in range(1, 8)]
EMAIL_PROPS = [f"email_{i}" for i in range(1, 8)]
PROP_SDR_NOTES = "eofy26_sdr_notes"
PROP_GENERATED_DATE = "eofy26_generated_date"
EMAIL_BODY_MAX_CHARS = 65000


def load_campaign_output(runner_temp):
    with open(os.path.join(runner_temp, "campaign_output.json"), encoding="utf-8") as f:
        return json.load(f)


def format_sdr_notes_plain(sdr_call_notes):
    lines = []

    lines.append("QUICK BRIEF")
    lines.append(sdr_call_notes.get("quick_brief", ""))
    lines.append("")

    lines.append("THE HOOK")
    lines.append(sdr_call_notes.get("the_hook", ""))
    lines.append("")

    call_map = [
        ("call_1_day6", "CALL 1 (Day 6)"),
        ("call_2_day20", "CALL 2 (Day 20)"),
        ("call_3_day40", "CALL 3 (Day 40)"),
    ]
    for key, label in call_map:
        call = sdr_call_notes.get(key) or {}
        lines.append(label)
        lines.append(f"Opening line: {call.get('opening_line', '')}")
        lines.append("Diagnostic questions:")
        for i, q in enumerate(call.get("diagnostic_questions", []), start=1):
            lines.append(f"  {i}. {q}")
        lines.append("")

    return "\n".join(lines)


def build_properties_payload(campaign, today):
    props = {}
    for i in range(1, 8):
        email_key = f"email_{i}"
        props[f"subject_{i}"] = campaign[email_key]["subject"]
        body = campaign[email_key]["body"]
        if len(body) > EMAIL_BODY_MAX_CHARS:
            log.warning(f"{email_key} body truncated from {len(body)} to {EMAIL_BODY_MAX_CHARS} chars (WR-03)")
            body = body[:EMAIL_BODY_MAX_CHARS]
        props[f"email_{i}"] = body
    props[PROP_SDR_NOTES] = format_sdr_notes_plain(campaign["sdr_call_notes"])
    props[PROP_GENERATED_DATE] = today
    return props


def write_properties(client, contact_id, properties):
    log.info(f"Writing {len(properties)} properties to contact {contact_id}: {list(properties.keys())}")
    client.crm.contacts.basic_api.update(
        contact_id,
        SimplePublicObjectInput(properties=properties),
    )


def build_note_html(campaign, contact_email, today_iso):
    parts = []
    parts.append("<h2>AI-Generated Outreach Campaign</h2>")
    parts.append(f"<p>Contact: {html.escape(contact_email)} | Generated: {html.escape(today_iso)}</p>")

    sdr = campaign.get("sdr_call_notes") or {}
    parts.append("<h3>SDR Quick Brief</h3>")
    parts.append(f"<p>{html.escape(sdr.get('quick_brief', ''))}</p>")

    parts.append("<h3>The Hook</h3>")
    parts.append(f"<p>{html.escape(sdr.get('the_hook', ''))}</p>")

    parts.append("<h3>SDR Call Plan</h3>")
    call_map = [
        ("call_1_day6", "Call 1 (Day 6)"),
        ("call_2_day20", "Call 2 (Day 20)"),
        ("call_3_day40", "Call 3 (Day 40)"),
    ]
    for key, label in call_map:
        call = sdr.get(key) or {}
        parts.append(f"<h4>{html.escape(label)}</h4>")
        parts.append(f"<p>Opening line: {html.escape(call.get('opening_line', ''))}</p>")
        questions = call.get("diagnostic_questions") or []
        if questions:
            parts.append("<ul>")
            for q in questions:
                parts.append(f"<li>{html.escape(str(q))}</li>")
            parts.append("</ul>")

    parts.append("<h3>7-Email Sequence</h3>")
    for i in range(1, 8):
        email_key = f"email_{i}"
        email = campaign.get(email_key) or {}
        parts.append(f"<h4>Email {i}</h4>")
        parts.append(f"<p><strong>Subject:</strong> {html.escape(email.get('subject', ''))}</p>")
        parts.append(f'<pre style="white-space: pre-wrap;">{html.escape(email.get("body", ""))}</pre>')

    return "\n".join(parts)


def create_note_engagement(contact_id, html_body, hubspot_key):
    try:
        resp = requests.post(
            "https://api.hubapi.com/engagements/v1/engagements",
            headers={
                "Authorization": f"Bearer {hubspot_key}",
                "Content-Type": "application/json",
            },
            json={
                "engagement": {"active": True, "type": "NOTE"},
                "associations": {"contactIds": [int(contact_id)]},
                "metadata": {"body": html_body},
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        note_id = result.get("engagement", {}).get("id", "unknown")
        log.info(f"Created HubSpot note engagement {note_id} on contact {contact_id}")
        return result
    except Exception as exc:
        log.warning(f"Note creation failed (non-fatal per WR-06): {exc}")
        return None


if __name__ == "__main__":
    runner_temp = os.environ.get("RUNNER_TEMP", ".")
    contact_id = os.environ["INPUT_CONTACT_ID"]
    contact_email = os.environ["INPUT_CONTACT_EMAIL"]
    hubspot_key = os.environ["HUBSPOT_API_KEY"]

    client = HubSpot(access_token=hubspot_key)
    campaign = load_campaign_output(runner_temp)
    today_iso = datetime.now(timezone.utc).date().isoformat()

    props_payload = build_properties_payload(campaign, today_iso)
    write_properties(client, contact_id, props_payload)
    log.info(f"Wrote {len(props_payload)} properties to contact {contact_id}")

    note_html = build_note_html(campaign, contact_email, today_iso)
    create_note_engagement(contact_id, note_html, hubspot_key)
    log.info(f"Pipeline complete for contact {contact_id} ({contact_email})")
