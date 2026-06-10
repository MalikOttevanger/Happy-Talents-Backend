# Happy Talents — Backend

FastAPI backend for the Happy Talents intake application. Turns a Plaud recording
into a ready-to-send proposal draft (transcript → AI analysis → top-3 matching →
Gmail draft).

See [`API.md`](./API.md), [`DATABASE.md`](./DATABASE.md) and
[`DATAFLOW.md`](./DATAFLOW.md) for the full design.

## Requirements

- Python 3.11+
- Google Chrome / Chromium (used by the Plaud scraper via Selenium)

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env   # Windows: copy .env.example .env
```

Then fill in `.env`. All values are optional for local development:

- **`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`** — when both are set, data is
  stored in Supabase. When empty, the backend uses an in-memory store so the
  endpoints work before the database is provisioned.
- **`CHROMIUM_PATH` / `CHROMEDRIVER_PATH`** — leave empty locally (Selenium
  Manager resolves the driver automatically). Set them in Docker / Cloud Run.
- **`PLAUD_PAGE_TIMEOUT`** — seconds to wait for the Plaud share page (default 20).

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- API base: <http://localhost:8000>
- Interactive docs (Swagger): <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

The frontend expects the backend at the URL set in its `VITE_API_BASE_URL`
(default `http://localhost:8000`).

## Try the transcript endpoint

```bash
curl -X POST http://localhost:8000/api/v1/transcripts \
  -H "Content-Type: application/json" \
  -d '{"plaud_url": "https://web.plaud.ai/s/your-share-link"}'
```

Returns `201` with the transcript id, the flattened `text`, the structured
`segments`, and the derived `duration_seconds`.

## Try the analysis endpoint

Requires `OPENAI_API_KEY` in `.env`. Pass the `transcript_id` from the step above:

```bash
curl -X POST http://localhost:8000/api/v1/analyses \
  -H "Content-Type: application/json" \
  -d '{"transcript_id": "the-transcript-uuid"}'
```

Returns `201` with the structured `opdracht_samenvatting` (client need +
competence profile). The LLM uses OpenAI Structured Outputs.

## Try the matching endpoint

Ranks the interimmer pool against an analysis (top-3, retrieve-then-rank: the LLM
picks an existing role as the single hard filter — `prompts/role_selection.yaml` —
then the backend queries that role and the LLM scores the group on soft criteria —
`prompts/top3_ranking.yaml`). Requires `OPENAI_API_KEY`, and interimmers in
Supabase (the pool is empty without it). Pass the `analysis_id` from the step
above:

```bash
curl -X POST http://localhost:8000/api/v1/matches \
  -H "Content-Type: application/json" \
  -d '{"analysis_id": "the-analysis-uuid", "limit": 3}'
```

Returns `201` with the ranked `shortlist` and an `aanbeveling`.

## Try the proposal endpoint

Generates the proposal email for selected candidates of a match. Hybrid: an
LLM-written intro (`prompts/proposal_intro.yaml`) plus a fixed template assembled
in `app/services/email_template.py`. `klant_naam` and `klant_bedrijf` come from the
frontend. Pass the `match_id` from the step above:

```bash
curl -X POST http://localhost:8000/api/v1/proposals \
  -H "Content-Type: application/json" \
  -d '{"match_id": "the-match-uuid", "klant_naam": "Nadine van Dijk", "klant_bedrijf": "Profilians"}'
```

Returns `201` with `subject` and `body_html`. Creating the actual Gmail draft
(`POST /api/v1/gmail/drafts`) is a separate endpoint added once Google OAuth2 is
configured.

## Prompts

All LLM prompts live in [`prompts/`](./prompts) as YAML (one file per prompt:
`system`, `user_template` [Jinja2], `model`, `temperature`, `version`). Edit them
without touching Python — they are loaded at request time.

## Tests

```bash
pytest
```

## Project layout

```
app/
  main.py                  # FastAPI app, routers, /health, CORS, Swagger
  core/config.py           # settings loaded from .env
  schemas/                 # Pydantic request/response models
  services/                # integrations (Plaud scraper, ...)
  repositories/            # persistence (Supabase + in-memory fallback)
  routers/                 # API endpoints (/api/v1/...)
tests/                     # pytest suite
```
