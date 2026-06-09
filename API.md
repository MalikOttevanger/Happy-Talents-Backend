# Happy Talents — API Specification

Contract-first API between the React frontend (`Happy-Talents-Frontend`) and the
FastAPI backend (`Happy-Talents-Backend`). This document is the agreed contract;
it is a living document and may evolve during development.

The backend uses Claude as its LLM provider. The provider is an internal
implementation detail and is intentionally **not** part of the public API
(no provider names in URLs).

## General conventions

- **Version prefix:** all endpoints live under `/api/v1/`.
- **Auth:** every endpoint requires a valid session token (Supabase Auth, Google
  provider — see [Auth](#8-auth--google-sso)). Requests without a valid token get `401`.
- **Persistence:** each pipeline step stores its result in Supabase and returns an
  `id`, so the next step references that id instead of resending payloads. This
  also serves audit/explainability.
- **Orchestrator vs steps:** the frontend talks to the **orchestrator**
  (`/intakes`). The individual step endpoints (`/transcripts`, `/analyses`,
  `/matches`) exist underneath for testability and reuse, and are normally called
  internally by the orchestrator.
- **Prompts:** all LLM prompts live in external YAML files under `prompts/`
  (one file per prompt: `system`, `user_template` [Jinja2], `model`,
  `temperature`, `version`), loaded via a small `PromptLoader` and validated with
  Pydantic. Kept light for the MVP — no prompt framework.
- **Errors:** standard HTTP status codes. Invalid LLM output that fails schema
  validation returns `422` (bad upstream data) or `502` (provider failure), never
  partial/broken data.

---

## Endpoint overview

| Feature | Endpoint(s) |
|---|---|
| Pipeline (orchestrator) | `POST /intakes`, `GET /intakes/{id}` |
| plaud-integration | `POST /transcripts` |
| ai-analysis | `POST /analyses` |
| top3-matching | `POST /matches` |
| gmail-draft | `POST /proposals`, `POST /gmail/drafts` |
| email-signature | `GET /users/me/signature` |
| kanban + multi-user | `GET /intakes`, `PATCH /intakes/{id}` |
| activecampaign-note-sync | `POST /intakes/{id}/activecampaign-note` *(provisional)* |
| google-sso | Supabase Auth (Google) + `google_credentials` table |

---

## Pipeline (orchestrator)

A single user action (pasting a Plaud link) triggers the whole chain:
transcript → analysis → matching. The chain runs **asynchronously**; the frontend
polls for the result. (Plaud fetch + 2× LLM call easily takes 30–60s, so a
synchronous request would time out.) This maps onto the existing UI
(`ProcessingIndicator`, kanban status `verwerken` → `review`).

### `POST /api/v1/intakes`
Starts the pipeline.

Request:
```json
{
  "plaud_url": "https://app.plaud.ai/share/abc123",
  "klant_naam": "Jan de Vries",
  "klant_bedrijf": "Acme BV",
  "bd_email": "bd@happytalents.nl"
}
```
Response `201`:
```json
{ "intake_id": "uuid", "status": "processing" }
```

### `GET /api/v1/intakes/{id}`
Returns status and (once ready) the full result.

Response `200`:
```json
{
  "intake_id": "uuid",
  "status": "review",
  "data": {
    "opdracht_samenvatting": { "...": "..." },
    "shortlist": [ { "...": "..." } ],
    "aanbeveling": "..."
  }
}
```
`status` transitions: `processing` → `review` → `verzonden`.

---

## 1. Transcript — `feature/plaud-integration`

### `POST /api/v1/transcripts`
Fetches the transcript for a Plaud share link (synchronous; stored in Supabase).

Request:
```json
{ "plaud_url": "https://app.plaud.ai/share/abc123" }
```
Response `201`:
```json
{
  "transcript_id": "uuid",
  "text": "Full transcript text...",
  "recorded_at": "2026-06-09T10:30:00Z",
  "duration_seconds": 1820,
  "source_url": "https://app.plaud.ai/share/abc123"
}
```

---

## 2. AI analysis — `feature/ai-analysis`

### `POST /api/v1/analyses`
Extracts the client need and competence profile from a transcript. Claude returns
**structured output** against a fixed JSON schema, validated with Pydantic.

Request:
```json
{ "transcript_id": "uuid" }
```
Response `201`:
```json
{
  "analysis_id": "uuid",
  "transcript_id": "uuid",
  "opdracht_samenvatting": {
    "klant_pijnpunten": "Maandrapportages lopen achter...",
    "gevraagde_competenties": ["Finance Management", "SAP"],
    "specialisme": "Finance Manager",
    "sector_ervaring": ["Retail", "FMCG"],
    "locatie_opdracht": "Amsterdam",
    "reistijd_voorkeur_minuten": 45,
    "startdatum": "2026-06-01",
    "contractvorm": "Interim",
    "budget_uur": 120,
    "duur_opdracht": "6 maanden",
    "bijzonderheden": null,
    "persoonlijke_context": null
  }
}
```
Shape of `opdracht_samenvatting` mirrors `OpdrachtSamenvatting` in the frontend
`types.ts`.

---

## 3. Matching — `feature/top3-matching`

### `POST /api/v1/matches`
Produces a ranked top-3 shortlist with explanations.

Request:
```json
{ "analysis_id": "uuid", "limit": 3 }
```
Response `201`:
```json
{
  "match_id": "uuid",
  "analysis_id": "uuid",
  "shortlist": [
    {
      "naam": "Martijn van der Berg",
      "matchscore": 94,
      "matchuitleg": "12 yrs Finance Management, SAP-certified, Amsterdam, immediately available.",
      "aandachtspunten": null,
      "beschikbaarheid": "Direct beschikbaar",
      "uurtarief": 115,
      "startdatum": "2026-06-01",
      "specialisme": "Finance Manager",
      "locatie": "Amsterdam",
      "competenties": ["Finance Management", "SAP"]
    }
  ],
  "aanbeveling": "Martijn is the strongest match: ..."
}
```
Candidate shape mirrors `Candidate` in `types.ts`.

### Matching logic — retrieve-then-rank with a single hard filter
1. **Role selection (LLM).** Claude picks the best-fitting `type_rol` from the
   analysis, constrained to roles that actually exist in the database (the backend
   supplies the allowed values). Claude returns **structured filter values only**,
   never raw SQL.
2. **Retrieve (backend).** The backend validates the chosen value against the
   allowed set and runs a **parameterized** Supabase query on `type_rol` only —
   the single hard filter, so the result is never empty due to over-filtering.
   `type_rol` is a list per candidate; a candidate matches if the role is in it.
3. **Rank (LLM).** Claude scores and ranks the full group on soft criteria
   (province/travel time, hourly rate, available hours, sector experience) into a
   top 3 with `matchscore`, `matchuitleg`, `aandachtspunten`. Rate and hours are
   negotiable with the client, so they are scored, not filtered out.

**No empty result possible:** because the role is always chosen from existing DB
roles, there is always ≥1 candidate. If the requested (very specific) role is not
an exact match, Claude picks the closest existing role and deliberately sets a
**low `matchscore`**, so the weak fit is visible in the result.

**Security:** the LLM never writes SQL; it only returns validated, enumerated
filter values. The backend builds the query — no injection or malformed-query risk.

---

## 4. Proposal email + Gmail draft — `feature/gmail-draft`

User-triggered **after** the review step (not part of the auto-pipeline).

### `POST /api/v1/proposals`
Generates the proposal email text for the selected candidates.

Request:
```json
{ "match_id": "uuid", "selected_candidate_ids": ["e1", "e2"] }
```
Response `201`:
```json
{
  "proposal_id": "uuid",
  "subject": "Voorstel interim Finance Manager — Acme BV",
  "body_html": "<p>Hi Jan,</p> ..."
}
```
The user may still edit `subject`/`body_html` in the UI before drafting.

**Generation = hybrid:** a fixed branded template (candidate blocks, hand-out link,
rate paragraph, sign-off) plus a Claude-written opening/needs section
(`email_intro`). Mirrors the existing `proposalEmail.ts`, which already prepended
an `email_intro` before the template. Intro prompt lives in
`prompts/proposal_intro.yaml`.

### `POST /api/v1/gmail/drafts`
Creates the email as a draft in the logged-in user's Gmail.

Request:
```json
{ "proposal_id": "uuid", "to": "klant@bedrijf.nl", "subject": "...", "body_html": "..." }
```
Response `201`:
```json
{ "gmail_draft_id": "..." }
```
The backend appends the user's signature (see below) to `body_html`, then creates
the draft via the Gmail API using the user's OAuth2 token.

---

## 5. Email signature — `feature/email-signature`

### `GET /api/v1/users/me/signature`
Reads the logged-in user's signature **from Gmail** (`users.settings.sendAs`).
No own storage, no write endpoint.

Response `200`:
```json
{ "signature_html": "<p>Met vriendelijke groet,<br/>Robert Hagen — Happy Talents</p>" }
```
When creating a draft, the backend fetches this live and appends it to the body
(a draft created via the API does **not** automatically get the Gmail web
signature). Requires OAuth2 scope `gmail.settings.basic` (read) in addition to
`gmail.compose` (drafts). The settings page shows the signature read-only.

---

## 6. Active Campaign note — `feature/activecampaign-note-sync` *(PROVISIONAL / OPEN)*

> Status: parked. The direction below is provisional, not final — should-have,
> not part of the core flow.

### `POST /api/v1/intakes/{id}/activecampaign-note`
The backend composes a note from the intake data and writes it via the Active
Campaign API to the **client contact** ("candidates X, Y, Z proposed for role R on
date D").

Response `201`:
```json
{ "note_id": "..." }
```
Provisional trigger: **automatically** once the intake reaches `verzonden`.

To clarify before building: exact note content, exact trigger condition, and the
client → Active Campaign contact-id mapping.

---

## 7. Inbox / kanban — `feature/kanban-board` + `feature/multi-user-sessions`

### `GET /api/v1/intakes`
Returns all intakes (summary per card). The frontend groups by `status` into
kanban columns (`verwerken` / `review` / `verzonden`). No pagination for the MVP.

Response `200`:
```json
[
  {
    "intake_id": "uuid",
    "klant_bedrijf": "Acme BV",
    "klant_naam": "Jan de Vries",
    "opdracht_titel": "Interim Finance Manager",
    "ontvangen_op": "2026-06-09T10:30:00Z",
    "status": "review",
    "voorgestelde_kandidaat": "Martijn van der Berg",
    "opgepakt_door": null
  }
]
```

### `PATCH /api/v1/intakes/{id}`
Updates status and/or owner. Dragging a card to another column = changing `status`.

Request (all fields optional):
```json
{ "status": "verzonden", "assigned_to": "user-uuid" }
```

**Assignment:** an intake arrives **without an owner**; a user manually sets the
owner via `assigned_to` (no automatic assignment to the creator). `opgepakt_door`
shows name/colour per user (multi-user, should-have).

---

## 8. Auth — `feature/google-sso`

- **Login / identity:** Supabase Auth with the Google provider → JWT, validated by
  the FastAPI backend. **All** endpoints require a valid token.
- **Gmail access:** on OAuth consent, request `access_type=offline` plus scopes
  `gmail.compose` and `gmail.settings.basic` → yields a refresh token.
- **Token storage:** the refresh token is stored **encrypted** per user in a
  Supabase table `google_credentials`; the backend mints short-lived access tokens
  on demand for Gmail calls (read signature, create draft).
- **Security (GDPR — see technical plan §7):** encryption at rest (KMS/pgcrypto),
  strict RLS (only the backend service role can read tokens), and graceful handling
  of revoked/expired tokens via a re-login flow. The refresh token is a long-lived,
  highly sensitive secret.

---

## Implementation note
On implementation, FastAPI auto-generates OpenAPI/Swagger at `/docs`, which becomes
the living, code-coupled version of this contract.
