"""Persistence for transcripts.

Stores transcripts in the Supabase `transcripts` table when credentials are
configured, and otherwise in a process-local dict so the endpoint stays testable
before the database is provisioned. The in-memory path logs a warning to make the
fallback obvious.
"""

import logging
import uuid

from app.core.config import get_settings
from app.repositories.supabase_client import get_supabase
from app.schemas.transcript import TranscriptResponse

logger = logging.getLogger(__name__)

# Development-only fallback store, keyed by transcript_id.
_memory_store: dict[str, TranscriptResponse] = {}


def save_transcript(
    text: str,
    segments_dump: list[dict],
    source_url: str,
    duration_seconds: int | None,
    job_id: str | None = None,
) -> TranscriptResponse:
    """Persist a transcript and return it with its generated id.

    `job_id` is optional: the standalone endpoint may create a transcript before
    it is linked to a job (the orchestrator passes one when it has it).
    """
    transcript_id = str(uuid.uuid4())
    settings = get_settings()

    if settings.supabase_enabled:
        row = {
            "id": transcript_id,
            "job_id": job_id,
            "text": text,
            "source_url": source_url,
            "duration_seconds": duration_seconds,
        }
        get_supabase().table("transcripts").insert(row).execute()
    else:
        logger.warning(
            "Supabase not configured — storing transcript %s in memory only.",
            transcript_id,
        )

    result = TranscriptResponse(
        transcript_id=transcript_id,
        text=text,
        segments=segments_dump,
        source_url=source_url,
        duration_seconds=duration_seconds,
    )

    if not settings.supabase_enabled:
        _memory_store[transcript_id] = result

    return result
