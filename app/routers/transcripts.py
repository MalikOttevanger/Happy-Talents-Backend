"""Transcript endpoint — `feature/plaud-integration`.

Implements `POST /api/v1/transcripts` from API.md (§1): fetch the transcript for a
Plaud share link, store it, and return it. Scraping is synchronous and slow, so it
runs in a threadpool to avoid blocking the event loop.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.repositories import transcripts as transcript_repo
from app.schemas.transcript import TranscriptCreateRequest, TranscriptResponse
from app.services.plaud import PlaudScrapeError, fetch_transcript

router = APIRouter(prefix="/api/v1", tags=["transcripts"])


@router.post(
    "/transcripts",
    response_model=TranscriptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transcript(payload: TranscriptCreateRequest) -> TranscriptResponse:
    """Fetch a Plaud transcript and persist it.

    Returns 502 when Plaud cannot be reached or the page has no transcript, so the
    caller never receives partial data.
    """
    source_url = str(payload.plaud_url)

    try:
        text, segments, duration_seconds = await run_in_threadpool(
            fetch_transcript, source_url
        )
    except PlaudScrapeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return transcript_repo.save_transcript(
        text=text,
        segments_dump=[seg.model_dump() for seg in segments],
        source_url=source_url,
        duration_seconds=duration_seconds,
    )
