# Campaign Brief: Personalised 7-Email Outreach Sequence

## Contact Summary

You are writing a personalised outreach campaign for the following contact:

- **Name:** {{contact.firstname}} {{contact.lastname}}
- **Email:** {{contact.email}}
- **Job Title:** {{contact.jobtitle}}
- **Company:** {{contact.company}}
- **Industry:** {{contact.industry}}
- **Company Size:** {{contact.num_employees}} employees
- **Location:** {{contact.city}}, {{contact.country}}
- **Website:** {{contact.website}}
- **HubSpot Owner ID:** {{contact.hubspot_owner_id}}

## Activity History

The following is a full record of all prior interactions with this contact, including emails sent and received, meeting notes, and call transcripts. Use this context to avoid repeating information already discussed, reference specific conversations, and personalise each email.

{{crm.full_activity_history}}

## Campaign Context

- **Today's Date:** {{campaign.current_date}}
- **EOFY Timing Context:** {{campaign.eofy_timing_context}}
- **Days Until EOFY (30 June):** {{campaign.days_to_eofy}}

The EOFY timing context will be one of:
- `pre_eofy_full` — more than 45 days until 30 June; full 45-day cadence applies
- `pre_eofy_compressed` — 45 days or fewer until 30 June; compress the cadence to fit before EOFY
- `post_eofy` — EOFY has passed; focus on post-EOFY follow-up themes

## Style Constraints

- Use Australian English spelling throughout (e.g., "personalise" not "personalize", "organisation" not "organization", "behaviour" not "behavior").
- Do not use em dashes (—) or en dashes (–) as sentence separators. Use commas, semicolons, or full stops instead.
- Keep each email body under 150 words. Be direct and conversational, not corporate.
- End every email with a clear, specific call to action (e.g., a question, a calendar link prompt, or a meeting request).
- Return only raw JSON. Do not wrap in markdown code fences. Do not include any prose before or after the JSON object.

## Required JSON Output Schema

```json
{
  "reasoning": {
    "drop_reason_classification": "...",
    "eofy_timing_context": "...",
    "meeting_evidence_check": "..."
  },
  "email_1": { "subject": "string, single line, no em/en dashes", "body": "string, multi-line plain text" },
  "email_2": { "subject": "...", "body": "..." },
  "email_3": { "subject": "...", "body": "..." },
  "email_4": { "subject": "...", "body": "..." },
  "email_5": { "subject": "...", "body": "..." },
  "email_6": { "subject": "...", "body": "..." },
  "email_7": { "subject": "...", "body": "..." },
  "sdr_call_notes": {
    "quick_brief": "string, plain text",
    "the_hook": "string, plain text",
    "call_1_day6": {
      "opening_line": "string",
      "diagnostic_questions": ["string", "string", "string"]
    },
    "call_2_day20": {
      "opening_line": "string",
      "diagnostic_questions": ["string", "string", "string"]
    },
    "call_3_day40": {
      "opening_line": "string",
      "diagnostic_questions": ["string", "string", "string"]
    }
  }
}
```

## Content Guidance

Write a 7-email outreach sequence targeting this contact around Australia's End of Financial Year (30 June). The sequence runs over 45 days, with emails spaced to build familiarity without overwhelming the contact. Adjust the urgency and framing based on the `eofy_timing_context`: if `pre_eofy_full`, introduce themes early and build gradually; if `pre_eofy_compressed`, lead with urgency and compress the cadence; if `post_eofy`, reframe around post-EOFY planning and budget reset.

Each email must be grounded in the contact's actual context: reference their industry, company size, job title, and any specific details from the activity history. If previous meetings or calls are logged, acknowledge the prior relationship rather than treating this as a cold outreach. If there is no activity history, open fresh but reference the company or industry specifically.

The `reasoning` object should document your decision-making: `drop_reason_classification` should classify whether this contact looks like a warm lead (prior meeting), a cold lead, or a re-engagement; `eofy_timing_context` should summarise how you adjusted the cadence based on the timing; `meeting_evidence_check` should note whether any prior meeting evidence was found in the activity history.

The `sdr_call_notes` section supports the SDR making live calls alongside the email sequence. `quick_brief` is a single paragraph summarising who this contact is and why they are worth calling, written as a briefing note for the SDR. `the_hook` is a one-sentence opener that captures the most compelling reason this contact would care right now. The three call objects (`call_1_day6`, `call_2_day20`, `call_3_day40`) correspond to scheduled SDR calls on days 6, 20, and 40 of the cadence. Each call object should include a natural, personalised `opening_line` and three `diagnostic_questions` that help the SDR qualify or deepen the relationship at that point in the sequence.

All content must be ready to use without editing: subjects should be specific and curiosity-inducing, bodies should be conversational and brief, and call scripts should read naturally when spoken aloud.
