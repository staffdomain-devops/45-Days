# GitHub Actions AI Email Campaign Automation

## What This Is

A GitHub Actions pipeline that generates personalised AI outreach email campaigns for sales contacts and writes the results back to HubSpot. When triggered (via Make.com watching a HubSpot list), it pulls contact data and Chorus AI call transcripts, builds a prompt, calls the Claude API to generate a 7-email sequence plus SDR call notes, and writes everything back to HubSpot contact properties and notes.

## Core Value

Sales reps get a fully-personalised, context-aware 7-email outreach sequence and SDR call notes generated automatically the moment a contact enters a target HubSpot list — zero manual effort.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Make.com scenario watches a HubSpot list and fires a GitHub Actions `workflow_dispatch` event with `contact_id` and `contact_email` inputs
- [ ] GitHub Actions workflow (`campaign.yml`) orchestrates all pipeline steps on `ubuntu-latest`
- [ ] `fetch_hubspot.py` — fetches contact properties, email/meeting engagement history (12 months), deal stage, owner names, and extracts Chorus conversation IDs from meeting notes
- [ ] `fetch_chorus.py` — fetches call transcripts from Chorus AI with silent fallback on 404/401/timeout; merges IDs from HubSpot notes, env override, and Chorus search API
- [ ] `compute_campaign_tokens.py` — computes campaign-specific runtime tokens (e.g. timing context, days to deadline)
- [ ] `generate_campaign.py` — substitutes `{{token.name}}` placeholders in `prompt_template.md`, calls Claude API, parses and validates JSON output
- [ ] `write_hubspot.py` — writes 7 email subjects + bodies and SDR notes back to HubSpot contact properties, creates a rich HTML note engagement on the contact
- [ ] All scripts implement exponential backoff retry via `tenacity` (6 attempts, max 60s delay); retry on 429 and 5xx only
- [ ] Dead-letter queue (DLQ): on unrecovered failure each script writes `failed_contacts.json` to `RUNNER_TEMP`
- [ ] Failure workflow steps upload `failed_contacts.json` artifact and POST a Teams/Slack webhook notification
- [ ] Campaign output uploaded as GitHub Actions artifact with 7-day retention
- [ ] Data flows between steps via `$RUNNER_TEMP` JSON temp files (no in-memory coupling)
- [ ] `prompt_template.md` defines the campaign brief with `{{token.name}}` substitution syntax; output JSON schema matches HubSpot property writer expectations
- [ ] HubSpot custom properties created before first run: `subject_1`–`subject_7`, `email_1`–`email_7`, SDR notes property, generated date property

### Out of Scope

- UI / dashboard — this is a backend pipeline only; visibility is via HubSpot and GitHub Actions logs
- Real-time triggering without Make.com — Make.com is the designated trigger layer
- Multi-contact batch runs in a single dispatch — each `workflow_dispatch` event handles one contact
- Storing transcripts or campaign output in a database — artifacts and HubSpot properties are the stores of record

## Context

This is a rebuild/re-implementation of an existing campaign automation system. The architecture is fully specified in `rebuild-prompt.md` in the project root. Key design patterns are established:

- Scripts are independent Python 3.12 modules; each reads its inputs from `RUNNER_TEMP` and writes its outputs to `RUNNER_TEMP`
- The workflow YAML wires them together in order; each step sets `INPUT_CONTACT_EMAIL` for DLQ attribution
- Chorus fallback is intentional — pipeline must not fail if call recordings are unavailable
- Australian English enforced in system prompt; no em/en dashes as separators; Claude returns raw JSON only
- The `prompt_template.md` and `compute_campaign_tokens.py` are the primary customisation points for each new campaign type

## Constraints

- **Tech stack**: Python 3.12, GitHub Actions, `hubspot-api-client>=12.0.0`, `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `anthropic>=0.30.0`, `tiktoken>=0.7.0`, `tenacity>=9.0.0`
- **AI model**: `claude-sonnet-4-6`, `max_tokens=16384` — chosen for output quality and JSON reliability
- **Auth**: Four secrets required — `HUBSPOT_API_KEY`, `CHORUS_API_TOKEN`, `ANTHROPIC_API_KEY`, `TEAMS_WEBHOOK_URL`
- **HubSpot API**: Private App token with contacts read/write, engagements read/write, owners read scopes
- **Chorus API**: Token-based auth (`Token XXXXXXXX`); transcript endpoint `GET https://chorus.ai/api/v1/conversations/{id}?fields=recording.utterances`
- **Email property limits**: HubSpot multi-line text properties cap at 65,000 chars each
- **Retry policy**: Anthropic SDK initialised with `max_retries=0` to prevent double-retry with tenacity

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `$RUNNER_TEMP` for inter-step data | Avoids in-memory coupling between workflow steps; survives step boundaries cleanly | — Pending |
| tenacity over Anthropic SDK built-in retry | Uniform retry behaviour across all three APIs (HubSpot, Chorus, Anthropic) with `Retry-After` header support | — Pending |
| Silent fallback on Chorus errors | Pipeline value is the email generation; missing transcripts degrade personalisation but must not block | — Pending |
| New HubSpot note per run (no overwrite) | Preserves audit trail of all generated campaign versions | — Pending |
| Make.com as trigger layer | Decouples HubSpot list watching from the pipeline; Make.com handles the webhook-to-workflow-dispatch translation | — Pending |
| Claude returns raw JSON only | Simplifies parsing; system prompt enforces no markdown wrapping | — Pending |

---
*Last updated: 2026-06-12 after initialization*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
