# Make.com Scenario Setup Guide

## Overview

This guide covers configuring the Make.com trigger layer (TRIG-01, TRIG-02) that watches a HubSpot list and automatically fires the `campaign.yml` GitHub Actions workflow when a contact is added.

## Prerequisites

- Make.com account with access to HubSpot and HTTP modules
- HubSpot Private App token with contacts read + list read permissions
- GitHub Personal Access Token (PAT) with `actions:write` scope on the `staffdomain-devops/45-Days` repo
- The target HubSpot List ID (the list contacts enter to trigger the campaign)

## Scenario Architecture

```
HubSpot: Watch List Members (new contact added)
  → GitHub: HTTP POST to workflow_dispatch API
```

## Step-by-Step Configuration

### Module 1: HubSpot — Watch List Memberships

1. In Make.com, create a new Scenario
2. Add the **HubSpot CRM** module: **Watch List Members** (or **Watch Contact Memberships**)
3. Configure:
   - **Connection**: Your HubSpot connection
   - **List ID**: The numeric ID of your target HubSpot list
   - **Fields to watch**: `contact_id`, `email`
4. Set the polling interval to your desired frequency (5 minutes is a sensible default)

> **Note**: If "Watch List Members" is not available in your HubSpot module version, use **HubSpot → Watch Contacts** filtered by list membership change, or use the **HubSpot CRM → Make a HubSpot API Call** module to poll `GET /contacts/v1/lists/{listId}/contacts/recent`.

### Module 2: HTTP — POST to GitHub Actions dispatch API

1. Add an **HTTP** module: **Make a Request**
2. Configure:

**URL:**
```
https://api.github.com/repos/staffdomain-devops/45-Days/actions/workflows/campaign.yml/dispatches
```

**Method:** `POST`

**Headers:**
| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <YOUR_GITHUB_PAT>` |
| `Accept` | `application/vnd.github+json` |
| `X-GitHub-Api-Version` | `2022-11-28` |
| `Content-Type` | `application/json` |

**Body type:** `Raw`

**Body content:**
```json
{
  "ref": "master",
  "inputs": {
    "contact_id": "{{1.contact_id}}",
    "contact_email": "{{1.email}}"
  }
}
```

Replace `{{1.contact_id}}` and `{{1.email}}` with the actual mapped fields from Module 1 output.

3. Set **Parse response**: ON
4. Expected response: `204 No Content` (GitHub returns 204 on successful dispatch)

### Module 3 (Optional): Error Handler

Add an **HTTP** error handler or a **Router** branch that:
- On non-204 response from GitHub: logs to a Make.com Data Store or sends a Slack/Teams alert
- This is optional but recommended for production

## Scenario Settings

| Setting | Value |
|---------|-------|
| Polling interval | 5 minutes (or 1 minute if your plan supports it) |
| Max executions | Unlimited (each contact triggers one execution) |
| Error handling | On error → Rollback + send notification |

## Testing the Scenario

1. Turn the scenario ON in development mode
2. Manually add a test contact to the target HubSpot list
3. Verify Make.com detects the addition and fires the HTTP request
4. Check GitHub Actions (`https://github.com/staffdomain-devops/45-Days/actions`) — the `AI Email Campaign Generation` workflow should appear as triggered
5. Confirm the workflow receives the correct `contact_id` and `contact_email` inputs in the run summary

## GitHub PAT Permissions Required

Create a Fine-grained Personal Access Token at `github.com/settings/tokens` with:
- **Repository access**: Only `staffdomain-devops/45-Days`
- **Permissions**: Actions (Read and write)

Store this token in Make.com as a connection credential (not hardcoded in the module config).

## HubSpot Custom Properties Setup (INFRA-03)

Before the first pipeline run, create these custom contact properties in HubSpot (Settings → Properties → Contact → Create property):

| Property Name | Type | Description |
|---------------|------|-------------|
| `subject_1` through `subject_7` | Single-line text | Email subject lines |
| `email_1` through `email_7` | Multi-line text | Email body content |
| `eofy26_sdr_notes` | Multi-line text | SDR call brief and scripts |
| `eofy26_generated_date` | Date | Date campaign was generated |
