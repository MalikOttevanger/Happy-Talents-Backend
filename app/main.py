"""FastAPI application entry point for the Happy Talents intake backend.

Wires up the routers behind the `/api/v1` prefix (see API.md). FastAPI serves the
living OpenAPI/Swagger contract at `/docs`.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analyses, matches, transcripts

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Happy Talents — Intake API",
    description="Backend for the Happy Talents intake application.",
    version="0.1.0",
)

# The frontend is a separate SPA; allow cross-origin calls. Tighten the origins
# once the deployed frontend URL is known.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcripts.router)
app.include_router(analyses.router)
app.include_router(matches.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe for Cloud Run."""
    return {"status": "ok", "service": "happy-talents-api"}
