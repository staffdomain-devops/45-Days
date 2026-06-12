"""Read pipeline inputs from $RUNNER_TEMP, assemble activity history, render prompt_template.md, call Claude, validate output, and write $RUNNER_TEMP/campaign_output.json."""

import os
import re
import json
import sys
import logging
from pathlib import Path

from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("generate_campaign")

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 16384
TOKEN_REGEX = re.compile(r"\{\{([a-z]+)\.([a-zA-Z0-9_.]+)\}\}")
REQUIRED_OUTPUT_KEYS = {
    "reasoning",
    "email_1", "email_2", "email_3", "email_4",
    "email_5", "email_6", "email_7",
    "sdr_call_notes",
}
BANNED_PUNCTUATION = {"—": ",", "–": ","}

SYSTEM_PROMPT = (
    "You are an expert sales SDR copywriter generating B2B outreach campaigns. "
    "Follow these rules strictly: "
    "(1) Use Australian English spelling throughout (e.g. 'organisation', 'personalise', 'colour'). "
    "(2) Never use em dashes (—) or en dashes (–) as sentence separators. Use commas, semicolons, or full stops instead. "
    "(3) Return only raw JSON matching the schema given in the user message. Do not wrap the JSON in markdown code fences. "
    "Do not include any prose before or after the JSON object. The response must start with { and end with }."
)


def load_inputs(runner_temp):
    with open(os.path.join(runner_temp, "hubspot_contact.json"), encoding="utf-8") as f:
        hubspot = json.load(f)
    with open(os.path.join(runner_temp, "chorus_transcripts.json"), encoding="utf-8") as f:
        transcripts = json.load(f)
    with open(os.path.join(runner_temp, "campaign_tokens.json"), encoding="utf-8") as f:
        tokens = json.load(f)
    return hubspot, transcripts, tokens


def assemble_activity_history(hubspot, transcripts):
    sections = []

    sections.append("=== EMAIL HISTORY ===")
    emails = hubspot.get("email_history", [])
    if emails:
        for e in emails:
            sections.append(
                f"[{e.get('timestamp', '')}] Subject: {e.get('subject', '')} | "
                f"From: {e.get('from', '')} | To: {e.get('to', '')}"
            )
            sections.append(e.get("body", ""))
            sections.append("---")
    else:
        sections.append("(none)")

    sections.append("")
    sections.append("=== MEETING ENGAGEMENTS ===")
    meetings = hubspot.get("meeting_engagements", [])
    if meetings:
        for m in meetings:
            sections.append(f"[{m.get('timestamp', '')}] Title: {m.get('title', '')}")
            sections.append(f"Notes: {m.get('notes', '')}")
            sections.append(f"Internal Notes: {m.get('internal_notes', '')}")
            attendees = m.get("attendees", [])
            sections.append(f"Attendees: {', '.join(attendees) if attendees else ''}")
            sections.append("---")
    else:
        sections.append("(none)")

    sections.append("")
    sections.append("=== CALL TRANSCRIPTS (CHORUS) ===")
    if transcripts:
        for t in transcripts:
            sections.append(str(t))
            sections.append("---")
    else:
        sections.append("(none)")

    return "\n".join(sections)


def flatten_namespace(prefix, value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from flatten_namespace(f"{prefix}.{k}", v)
    else:
        yield prefix, str(value) if value is not None else ""


def substitute_tokens(template, contact_props, full_activity_history, campaign_tokens):
    substitutions = {}
    for key, val in flatten_namespace("contact", contact_props):
        substitutions[key] = val
    substitutions["crm.full_activity_history"] = full_activity_history
    for key, val in flatten_namespace("campaign", campaign_tokens):
        substitutions[key] = val

    def replace_fn(match):
        token_key = f"{match.group(1)}.{match.group(2)}"
        if token_key in substitutions:
            return substitutions[token_key]
        log.warning(f"Unresolved token: {match.group(0)}")
        return match.group(0)

    return TOKEN_REGEX.sub(replace_fn, template)


def strip_banned_punctuation(obj):
    if isinstance(obj, str):
        for bad, good in BANNED_PUNCTUATION.items():
            obj = obj.replace(bad, good)
        return obj
    if isinstance(obj, dict):
        return {k: strip_banned_punctuation(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strip_banned_punctuation(item) for item in obj]
    return obj


def validate_output(data):
    if not isinstance(data, dict):
        raise ValueError(f"Claude response is not a JSON object, got: {type(data)}")
    missing = REQUIRED_OUTPUT_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Claude response missing required keys: {missing}")
    for i in range(1, 8):
        key = f"email_{i}"
        email = data[key]
        if not isinstance(email, dict) or "subject" not in email or "body" not in email:
            raise ValueError(f"{key} must be a dict with 'subject' and 'body' string keys")
    sdr = data.get("sdr_call_notes", {})
    if not isinstance(sdr, dict):
        raise ValueError("sdr_call_notes must be a dict")
    required_sdr_keys = {"quick_brief", "the_hook", "call_1_day6", "call_2_day20", "call_3_day40"}
    missing_sdr = required_sdr_keys - set(sdr.keys())
    if missing_sdr:
        raise ValueError(f"sdr_call_notes missing required keys: {missing_sdr}")


def call_claude(rendered_prompt):
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": rendered_prompt}],
    )
    if not resp.content:
        raise ValueError("Claude returned empty content")
    raw = "".join(getattr(block, "text", "") for block in resp.content).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error(f"Claude response was not valid JSON. First 500 chars:\n{raw[:500]}")
        raise


if __name__ == "__main__":
    runner_temp = os.environ.get("RUNNER_TEMP", ".")
    hubspot, transcripts, tokens = load_inputs(runner_temp)

    activity_history = assemble_activity_history(hubspot, transcripts)

    template_path = Path(__file__).resolve().parent.parent / "prompt_template.md"
    template = template_path.read_text(encoding="utf-8")
    rendered = substitute_tokens(template, hubspot["contact_properties"], activity_history, tokens)

    log.info(f"Rendered prompt: {len(rendered)} chars, {len(activity_history)} chars of activity history")

    log.info(f"Calling Claude model={MODEL}, max_tokens={MAX_TOKENS}, prompt_chars={len(rendered)}")
    raw_output = call_claude(rendered)

    output = strip_banned_punctuation(raw_output)
    validate_output(output)

    out_path = os.path.join(runner_temp, "campaign_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    log.info(f"Wrote {out_path} — {len(output)} top-level keys")
