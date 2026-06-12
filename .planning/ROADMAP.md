# Roadmap: GitHub Actions AI Email Campaign Automation

**Created:** 2026-06-12
**Granularity:** Coarse
**Coverage:** 43/43 requirements mapped

## Phases

- [ ] **Phase 1: Core Pipeline Skeleton** - End-to-end pipeline: fetch HubSpot data, generate campaign with Claude, write results back to HubSpot
- [ ] **Phase 2: Chorus AI Integration** - Enrich campaign personalisation with call transcript data; graceful fallback if unavailable
- [ ] **Phase 3: Reliability Hardening** - Production-grade retry, DLQ records, failure artifact uploads, Teams/Slack notifications
- [ ] **Phase 4: Make.com Trigger Wiring** - Full trigger flow: Make.com detects HubSpot list additions and fires workflow_dispatch

## Summary Table

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 1 | Core Pipeline Skeleton | Thin but functional end-to-end pipeline | TRIG-03, PIPE-01–04, PIPE-07, HS-01–07, TOK-01–02, AI-01–07, WR-01–06, INFRA-01–03 | 4 criteria |
| 2 | Chorus AI Integration | Call transcript enrichment with graceful fallback | CHO-01, CHO-02, CHO-03, CHO-04 | 3 criteria |
| 3 | Reliability Hardening | Production-grade retry, DLQ, and failure notifications | ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, PIPE-05, PIPE-06 | 4 criteria |
| 4 | Make.com Trigger Wiring | Full automated trigger flow from HubSpot list to pipeline | TRIG-01, TRIG-02 | 3 criteria |

## Phase Details

### Phase 1: Core Pipeline Skeleton
**Goal:** A working end-to-end pipeline that fetches HubSpot data, generates a campaign with Claude, and writes results back to HubSpot — thin but functional.
**Mode:** mvp
**Depends on:** Nothing
**Requirements:** TRIG-03, PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-07, HS-01, HS-02, HS-03, HS-04, HS-05, HS-06, HS-07, TOK-01, TOK-02, AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07, WR-01, WR-02, WR-03, WR-04, WR-05, WR-06, INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. A manually-dispatched workflow_dispatch run (with a real contact_id and contact_email) completes without error and writes all 7 email subjects, 7 email bodies, SDR notes, and generation date to the HubSpot contact record
  2. A new HubSpot note engagement appears on the contact after each run, containing the campaign brief and SDR call notes in rich HTML format
  3. The campaign_output.json artifact is visible in GitHub Actions with 7-day retention after a successful run
  4. All inter-step data (hubspot_contact.json, campaign_tokens.json, campaign_output.json) is written to and read from $RUNNER_TEMP — no step shares in-memory state with another
**Plans:** TBD

### Phase 2: Chorus AI Integration
**Goal:** Enrich campaign personalisation with call transcript data from Chorus AI — pipeline must continue gracefully if Chorus is unavailable.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** CHO-01, CHO-02, CHO-03, CHO-04
**Success Criteria** (what must be TRUE):
  1. When valid Chorus conversation IDs exist (from HubSpot meeting notes, env override, or Chorus search), the generated emails reference specific context from the call transcripts
  2. When Chorus returns 404, 401, or times out, the pipeline run still completes successfully and writes campaign output to HubSpot — no error is raised and the log shows a silent fallback message
  3. chorus_transcripts.json is written to $RUNNER_TEMP as an array; an empty array is written when no transcripts are available, so downstream steps never fail on a missing file
**Plans:** TBD

### Phase 3: Reliability Hardening
**Goal:** All scripts implement production-grade retry with tenacity, write DLQ records on unrecovered failure, and the workflow uploads failure artifacts and sends Teams/Slack notifications.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, PIPE-05, PIPE-06
**Success Criteria** (what must be TRUE):
  1. When a HubSpot, Chorus, or Anthropic API call returns 429 or 5xx, the script retries up to 6 attempts with exponential backoff before failing — a 4xx (other than 429) causes immediate permanent failure with no retry
  2. When a script exhausts all retries, a failed_contacts.json record appears in $RUNNER_TEMP containing contact_id, contact_email, failed_step, a truncated error message, timestamp, and retry_count
  3. When any pipeline step fails, the failed_contacts.json is uploaded as a GitHub Actions artifact and a notification is POSTed to the configured Teams/Slack webhook containing the contact email, failed step name, error excerpt, and a direct link to the run log
  4. The Anthropic SDK is initialised with max_retries=0 on every run — SDK-level and tenacity retries never stack
**Plans:** TBD

### Phase 4: Make.com Trigger Wiring
**Goal:** The full end-to-end trigger flow works — Make.com detects HubSpot list additions and fires the GitHub Actions workflow_dispatch event.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** TRIG-01, TRIG-02
**Success Criteria** (what must be TRUE):
  1. Adding a contact to the target HubSpot list causes Make.com to detect the addition and automatically fire a workflow_dispatch event to GitHub Actions within the Make.com scenario polling interval
  2. The triggered GitHub Actions run receives the correct contact_id and contact_email inputs matching the contact that was added to the list, and the full pipeline completes end-to-end
  3. No manual intervention is required between a contact being added to the HubSpot list and the campaign appearing on that contact's HubSpot record
**Plans:** TBD

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Pipeline Skeleton | 0/? | Not started | - |
| 2. Chorus AI Integration | 0/? | Not started | - |
| 3. Reliability Hardening | 0/? | Not started | - |
| 4. Make.com Trigger Wiring | 0/? | Not started | - |

---
*Roadmap created: 2026-06-12*
