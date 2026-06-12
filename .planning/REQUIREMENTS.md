# Requirements: GitHub Actions AI Email Campaign Automation

**Defined:** 2026-06-12
**Core Value:** Sales reps get a fully-personalised, context-aware 7-email outreach sequence and SDR call notes generated automatically the moment a contact enters a target HubSpot list — zero manual effort.

## v1 Requirements

### Trigger Layer

- [ ] **TRIG-01**: Make.com scenario detects when a contact is added to a specific HubSpot list
- [ ] **TRIG-02**: Make.com fires a GitHub Actions `workflow_dispatch` event via the GitHub API with `contact_id` and `contact_email` inputs
- [ ] **TRIG-03**: GitHub Actions workflow accepts `contact_id` and `contact_email` as `workflow_dispatch` inputs

### Pipeline Orchestration

- [ ] **PIPE-01**: Workflow file `.github/workflows/campaign.yml` runs on `ubuntu-latest` with a defined `working-directory` pointing to the project subfolder
- [ ] **PIPE-02**: Pipeline steps execute in order: fetch_hubspot → fetch_chorus → compute_tokens → generate_campaign → write_hubspot
- [ ] **PIPE-03**: Data flows between steps via JSON temp files in `$RUNNER_TEMP` (no in-memory coupling between steps)
- [ ] **PIPE-04**: Campaign output JSON uploaded as a GitHub Actions artifact with 7-day retention
- [ ] **PIPE-05**: On pipeline failure, `failed_contacts.json` is copied from `RUNNER_TEMP` and uploaded as a `failed-contacts` artifact
- [ ] **PIPE-06**: On pipeline failure, a notification is POSTed to a Teams/Slack webhook with contact email, failed step, error excerpt, and run log link
- [ ] **PIPE-07**: Required secrets configured in repo: `HUBSPOT_API_KEY`, `CHORUS_API_TOKEN`, `ANTHROPIC_API_KEY`, `TEAMS_WEBHOOK_URL`

### HubSpot Data Fetching

- [ ] **HS-01**: `fetch_hubspot.py` fetches a defined list of contact properties including `firstname`, `lastname`, `email`, `jobtitle`, `company`, `industry`, `num_employees`, `city`, `country`, `website`, `hubspot_owner_id`
- [ ] **HS-02**: Script fetches all email engagements from the past 12 months and strips HTML from email bodies
- [ ] **HS-03**: Script fetches all meeting engagements from the past 12 months including notes, internal notes, and attendees
- [ ] **HS-04**: Script fetches CRM meeting objects via the v4 associations API (covers scheduler-created meetings)
- [ ] **HS-05**: Script extracts Chorus conversation IDs from meeting notes via regex matching `chorus.ai/meeting/XXXXXXXX` URLs
- [ ] **HS-06**: Script resolves owner first names from owner IDs via HubSpot owners API
- [ ] **HS-07**: Script writes `hubspot_contact.json` to `$RUNNER_TEMP` with keys: `contact_properties`, `deal_stage`, `email_history`, `meeting_engagements`, `chorus_conversation_ids`

### Chorus AI Transcript Fetching

- [ ] **CHO-01**: `fetch_chorus.py` fetches call transcripts using conversation IDs merged from three sources: HubSpot meeting note regex, `INPUT_CHORUS_IDS` env var override, and Chorus v3 engagements API search by company name
- [ ] **CHO-02**: Transcript fetch uses `GET https://chorus.ai/api/v1/conversations/{id}?fields=recording.utterances`
- [ ] **CHO-03**: Script silently falls back on 404, 401, or timeout errors — pipeline continues with empty transcripts
- [ ] **CHO-04**: Script writes `chorus_transcripts.json` to `$RUNNER_TEMP` as an array of transcript objects

### Campaign Token Computation

- [ ] **TOK-01**: `compute_campaign_tokens.py` computes campaign-specific runtime tokens needed for prompt substitution (e.g. current date, timing context labels, days to deadline)
- [ ] **TOK-02**: Script writes `campaign_tokens.json` to `$RUNNER_TEMP`

### AI Generation

- [ ] **AI-01**: `generate_campaign.py` reads `hubspot_contact.json`, `chorus_transcripts.json`, and `campaign_tokens.json` from `$RUNNER_TEMP`
- [ ] **AI-02**: Script assembles an `activity_history` string from email threads + meeting notes + call transcripts as labelled blocks
- [ ] **AI-03**: Script substitutes `{{token.name}}` placeholders in `prompt_template.md` with values from all data sources (`contact.*`, `crm.full_activity_history`, `campaign.*` namespaces)
- [ ] **AI-04**: Script calls `claude-sonnet-4-6` with `max_tokens=16384` and a system prompt enforcing: Australian English, no em/en dashes as separators, return only raw JSON
- [ ] **AI-05**: Script validates the Claude response contains all required JSON keys and strips any banned punctuation
- [ ] **AI-06**: Script writes `campaign_output.json` to `$RUNNER_TEMP`
- [ ] **AI-07**: `prompt_template.md` defines the complete campaign brief with `{{token.name}}` substitution placeholders; the JSON output schema matches what `write_hubspot.py` expects

### HubSpot Writing

- [ ] **WR-01**: `write_hubspot.py` reads `campaign_output.json` from `$RUNNER_TEMP`
- [ ] **WR-02**: Script writes `subject_1` through `subject_7` as single-line text contact properties (overwrite each run)
- [ ] **WR-03**: Script writes `email_1` through `email_7` as multi-line text contact properties up to 65,000 chars each (overwrite each run)
- [ ] **WR-04**: Script writes SDR call notes and generation date to their respective custom contact properties (overwrite each run)
- [ ] **WR-05**: Script creates a new HubSpot note engagement on the contact with a rich HTML body containing campaign brief + SDR call notes (new note per run, no overwrite)
- [ ] **WR-06**: Note creation failure is non-fatal — script logs a warning and continues

### Error Handling & Reliability

- [ ] **ERR-01**: All four Python scripts implement exponential backoff retry using `tenacity` with `wait_random_exponential(multiplier=1, min=1, max=60)` plus `Retry-After` header support
- [ ] **ERR-02**: Retry policy: `stop_after_attempt(6) | stop_after_delay(60)`; retry only on 429 and 5xx status codes; 4xx (except 429) are permanent failures with no retry
- [ ] **ERR-03**: Anthropic SDK initialised with `max_retries=0` to prevent double-retry layering with tenacity
- [ ] **ERR-04**: On unrecovered failure, each script writes a DLQ record to `$RUNNER_TEMP/failed_contacts.json` containing `contact_id`, `contact_email`, `failed_step`, `error_message` (truncated to 2000 chars), `timestamp`, and `retry_count`
- [ ] **ERR-05**: HubSpot SDK exceptions checked via `e.status` on `ApiException`; requests library errors checked via `e.response.status_code` on `HTTPError`

### Project Infrastructure

- [ ] **INFRA-01**: Project lives in a subfolder (e.g. `45_DAYS/`) within the repo; `working-directory` in workflow YAML points to this subfolder
- [ ] **INFRA-02**: `requirements.txt` pins all dependencies: `hubspot-api-client>=12.0.0`, `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `anthropic>=0.30.0`, `tiktoken>=0.7.0`, `tenacity>=9.0.0`
- [ ] **INFRA-03**: HubSpot custom contact properties created before first run: `subject_1`–`subject_7` (single-line text), `email_1`–`email_7` (multi-line text), SDR notes property (multi-line text), generated date property (date)

## v2 Requirements

### Enhanced Personalisation

- **ENH-01**: Automatic detection of contact's preferred language with localised email generation
- **ENH-02**: A/B variant generation — produce two versions of key emails for split testing
- **ENH-03**: Integration with LinkedIn Sales Navigator for additional contact context

### Observability

- **OBS-01**: Structured logging to a central store (e.g. DataDog, CloudWatch) rather than GitHub Actions logs only
- **OBS-02**: Pipeline run metrics dashboard showing success rate, generation time, token usage per run

### Multi-Contact Batch Mode

- **BATCH-01**: Single workflow dispatch accepts a list of contact IDs and processes them in parallel jobs

## Out of Scope

| Feature | Reason |
|---------|--------|
| UI / admin dashboard | Backend pipeline only; visibility is via HubSpot and GitHub Actions |
| Real-time trigger without Make.com | Make.com is the designated trigger layer; direct webhook-to-Actions is v2 |
| Multi-contact single dispatch | Each dispatch is one contact; batch mode is v2 |
| Storing output in a database | HubSpot properties + GitHub Actions artifacts are the stores of record |
| Email sending | Pipeline generates content only; sending is handled by HubSpot sequences |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRIG-01 | TBD | Pending |
| TRIG-02 | TBD | Pending |
| TRIG-03 | TBD | Pending |
| PIPE-01 | TBD | Pending |
| PIPE-02 | TBD | Pending |
| PIPE-03 | TBD | Pending |
| PIPE-04 | TBD | Pending |
| PIPE-05 | TBD | Pending |
| PIPE-06 | TBD | Pending |
| PIPE-07 | TBD | Pending |
| HS-01 | TBD | Pending |
| HS-02 | TBD | Pending |
| HS-03 | TBD | Pending |
| HS-04 | TBD | Pending |
| HS-05 | TBD | Pending |
| HS-06 | TBD | Pending |
| HS-07 | TBD | Pending |
| CHO-01 | TBD | Pending |
| CHO-02 | TBD | Pending |
| CHO-03 | TBD | Pending |
| CHO-04 | TBD | Pending |
| TOK-01 | TBD | Pending |
| TOK-02 | TBD | Pending |
| AI-01 | TBD | Pending |
| AI-02 | TBD | Pending |
| AI-03 | TBD | Pending |
| AI-04 | TBD | Pending |
| AI-05 | TBD | Pending |
| AI-06 | TBD | Pending |
| AI-07 | TBD | Pending |
| WR-01 | TBD | Pending |
| WR-02 | TBD | Pending |
| WR-03 | TBD | Pending |
| WR-04 | TBD | Pending |
| WR-05 | TBD | Pending |
| WR-06 | TBD | Pending |
| ERR-01 | TBD | Pending |
| ERR-02 | TBD | Pending |
| ERR-03 | TBD | Pending |
| ERR-04 | TBD | Pending |
| ERR-05 | TBD | Pending |
| INFRA-01 | TBD | Pending |
| INFRA-02 | TBD | Pending |
| INFRA-03 | TBD | Pending |

**Coverage:**
- v1 requirements: 43 total
- Mapped to phases: 0 (traceability updated after roadmap creation)
- Unmapped: 43 ⚠️

---
*Requirements defined: 2026-06-12*
*Last updated: 2026-06-12 after initial definition*
