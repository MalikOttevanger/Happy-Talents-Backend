"""Request/response models for the transcript endpoint.

Mirrors the `POST /api/v1/transcripts` contract in `API.md` (§1) and the
`transcripts` table in `DATABASE.md`.
"""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class TranscriptSegment(BaseModel):
    """A single line of the transcript as scraped from the Plaud share page."""

    timestamp: str = Field(description="Relative time marker, e.g. '00:42'.")
    speaker: str = Field(description="Speaker label as shown by Plaud.")
    text: str = Field(description="Spoken text for this segment.")


class TranscriptCreateRequest(BaseModel):
    """Body for `POST /api/v1/transcripts`."""

    plaud_url: HttpUrl = Field(description="Plaud share link of the intake recording.")


class TranscriptResponse(BaseModel):
    """Result of fetching and storing a transcript.

    `text` is the full transcript flattened to a readable string; `segments`
    keeps the structured per-line data for downstream use (e.g. analysis).
    """

    transcript_id: str
    text: str
    segments: list[TranscriptSegment]
    source_url: str
    duration_seconds: int | None = None
    recorded_at: datetime | None = None
