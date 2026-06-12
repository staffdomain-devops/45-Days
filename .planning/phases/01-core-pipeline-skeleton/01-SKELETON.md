# Walking Skeleton: Phase 1 — Core Pipeline Skeleton

## What It Proves

The skeleton proves the entire pipeline data flow works end-to-end on `ubuntu-latest`:

1. A manually-dispatched `workflow_dispatch` accepts `contact_id` and `contact_email`
2. Step 1 (`fetch_hubspot.py`) successfully reads a real HubSpot contact and writes `hubspot_contact.json` to `$RUNNER_TEMP`
3. Step 2 (`fetch_chorus.py`) writes an empty array to `chorus_transcripts.json` (Phase 2 stub — proves the file contract works)
4. Step 3 (`compute_campaign_tokens.py`) writes `campaign_tokens.json` to `$RUNNER_TEMP`
5. Step 4 (`generate_campaign.py`) reads all three JSON files, substitutes `{{token.name}}` placeholders in `prompt_template.md`, calls `claude-sonnet-4-6`, and writes `campaign_output.json` to `$RUNNER_TEMP`
6. Step 5 (`write_hubspot.py`) reads `campaign_output.json` and writes 7 subjects + 7 email bodies + SDR notes + generated date to the HubSpot contact, then creates a note engagement
7. `campaign_output.json` is uploaded as a GitHub Actions artifact with 7-day retention

The skeleton proves: **every step's JSON contract works, secrets are wired correctly, Claude responds with valid JSON, and HubSpot accepts the writes.**

## Skeleton Scope

The skeleton is the **thinnest possible** version of each component:

### Workflow (`.github/workflows/campaign.yml`)
- `workflow_dispatch` with `contact_id` and `contact_email` inputs
- `working-directory: 45_DAYS/` on `ubuntu-latest`
- All five script steps in order
- `actions/upload-artifact@v4` for `campaign_output.json` (7-day retention)
- All four secrets wired as env vars: `HUBSPOT_API_KEY`, `CHORUS_API_TOKEN`, `ANTHROPIC_API_KEY`, `TEAMS_WEBHOOK_URL`

### Project Structure
```
45_DAYS/
├── scripts/
│   ├── fetch_hubspot.py
│   ├── fetch_chorus.py           # Phase 2 stub: writes empty array
│   ├── compute_campaign_tokens.py
│   ├── generate_campaign.py
│   └── write_hubspot.py
├── prompt_template.md
├── requirements.txt
└── (no CLAUDE.md needed yet)
.github/
└── workflows/
    └── campaign.yml
```

### Per-Script Minimum

| Script | Minimum Viable Behavior |
|---|---|
| `fetch_hubspot.py` | Fetch contact props + email history + meeting engagements (past 12 months) + Chorus ID regex extraction + owner resolution. Write full schema JSON. No tenacity yet (Phase 3). |
| `fetch_chorus.py` | Write `[]` (empty array) to `$RUNNER_TEMP/chorus_transcripts.json`. Log "Chorus disabled in Phase 1 — Phase 2 stub". |
| `compute_campaign_tokens.py` | Compute `current_date` (today, AU format) + `eofy_timing_context` + `days_to_eofy`. Write `campaign_tokens.json`. |
| `generate_campaign.py` | Read all three JSON files, assemble activity_history, substitute `{{token.name}}`, call Claude (`claude-sonnet-4-6`, `max_tokens=16384`, `max_retries=0`), validate keys (`email_1`–`email_7`, `sdr_call_notes`), strip em/en dashes, write `campaign_output.json`. |
| `write_hubspot.py` | Write 7 subject + 7 email + SDR notes + generated date properties. Create note engagement (non-fatal on note failure). |

### Out of Scope (Deferred to Later Phases)
- Tenacity retry / DLQ writes / failure notification → **Phase 3**
- Real Chorus API fetching → **Phase 2**
- Make.com trigger → **Phase 4**

## End-to-End Flow

```
[Manual workflow_dispatch with contact_id + contact_email]
         │
         ▼
┌────────────────────────────┐
│ fetch_hubspot.py           │ ─── writes ──▶ $RUNNER_TEMP/hubspot_contact.json
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ fetch_chorus.py (stub)     │ ─── writes ──▶ $RUNNER_TEMP/chorus_transcripts.json (= [])
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ compute_campaign_tokens.py │ ─── writes ──▶ $RUNNER_TEMP/campaign_tokens.json
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ generate_campaign.py       │ ─── reads all 3 JSON files
│ - assembles activity hist  │ ─── substitutes {{token.name}} in prompt_template.md
│ - calls claude-sonnet-4-6  │ ─── writes ──▶ $RUNNER_TEMP/campaign_output.json
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ write_hubspot.py           │ ─── writes 7 subjects, 7 emails, SDR notes, gen date
│                            │ ─── creates HubSpot note engagement
└────────────────────────────┘
         │
         ▼
[actions/upload-artifact@v4 uploads campaign_output.json — 7-day retention]
```

## Success Signals

After running the workflow on a real test contact:

1. **GitHub Actions run finishes green** — all 5 script steps succeed
2. **Artifact visible** — `campaign_output.json` artifact appears in the run with 7-day retention
3. **HubSpot contact has new data** — visit the contact in HubSpot; `subject_1` through `subject_7`, `email_1` through `email_7`, `eofy26_sdr_notes`, and `eofy26_generated_date` properties are populated
4. **HubSpot note exists** — a new note engagement appears on the contact's activity timeline with HTML body containing the campaign brief + SDR call notes
5. **Logs show correct flow** — each script step logs the file it wrote (`hubspot_contact.json`, `chorus_transcripts.json` = `[]`, `campaign_tokens.json`, `campaign_output.json`)
6. **Re-running overwrites** — running the workflow a second time on the same contact updates `subject_1`–`subject_7` and `email_1`–`email_7` (overwrite) but adds a NEW note (not overwrite)

## Architectural Decisions (set here, kept stable through Phase 4)

| Decision | Choice | Reason |
|---|---|---|
| Project subfolder name | `45_DAYS/` | Matches project naming; sets `working-directory` in workflow YAML |
| Python version | `3.12` | Required by REQUIREMENTS.md tech stack |
| Inter-step transport | JSON files in `$RUNNER_TEMP` | Required by PIPE-03; no in-memory coupling |
| Anthropic SDK init | `max_retries=0` | Required by ERR-03; prevents Phase 3 tenacity stacking |
| Claude model | `claude-sonnet-4-6` | Locked by REQUIREMENTS.md AI-04 |
| `max_tokens` | `16384` | Locked by REQUIREMENTS.md AI-04 |
| HubSpot SDK | `hubspot-api-client>=12.0.0` | Locked by REQUIREMENTS.md INFRA-02 |
| Chorus stub strategy | `fetch_chorus.py` writes `[]` always in Phase 1 | Keeps downstream contract stable; Phase 2 replaces internals only |
| SDR notes property name | `eofy26_sdr_notes` | Carried from existing campaign convention in rebuild-prompt.md |
| Generated date property | `eofy26_generated_date` | Carried from existing campaign convention in rebuild-prompt.md |
| Workflow file path | `.github/workflows/campaign.yml` | Locked by PIPE-01 |
| Artifact retention | 7 days | Locked by PIPE-04 |
