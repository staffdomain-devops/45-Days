<!-- GSD:project-start source:PROJECT.md -->
## Project

**GitHub Actions AI Email Campaign Automation**

A GitHub Actions pipeline that generates personalised AI outreach email campaigns for sales contacts and writes the results back to HubSpot. When triggered (via Make.com watching a HubSpot list), it pulls contact data and Chorus AI call transcripts, builds a prompt, calls the Claude API to generate a 7-email sequence plus SDR call notes, and writes everything back to HubSpot contact properties and notes.

**Core Value:** Sales reps get a fully-personalised, context-aware 7-email outreach sequence and SDR call notes generated automatically the moment a contact enters a target HubSpot list — zero manual effort.

### Constraints

- **Tech stack**: Python 3.12, GitHub Actions, `hubspot-api-client>=12.0.0`, `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `anthropic>=0.30.0`, `tiktoken>=0.7.0`, `tenacity>=9.0.0`
- **AI model**: `claude-sonnet-4-6`, `max_tokens=16384` — chosen for output quality and JSON reliability
- **Auth**: Four secrets required — `HUBSPOT_API_KEY`, `CHORUS_API_TOKEN`, `ANTHROPIC_API_KEY`, `TEAMS_WEBHOOK_URL`
- **HubSpot API**: Private App token with contacts read/write, engagements read/write, owners read scopes
- **Chorus API**: Token-based auth (`Token XXXXXXXX`); transcript endpoint `GET https://chorus.ai/api/v1/conversations/{id}?fields=recording.utterances`
- **Email property limits**: HubSpot multi-line text properties cap at 65,000 chars each
- **Retry policy**: Anthropic SDK initialised with `max_retries=0` to prevent double-retry with tenacity
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
