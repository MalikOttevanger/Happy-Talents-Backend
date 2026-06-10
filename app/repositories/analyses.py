"""Persistence for analyses.

Stores analyses in the Supabase `analyses` table when configured, otherwise in a
process-local dict (development fallback). Mirrors transcripts.py.
"""

import logging
import uuid

from app.core.config import get_settings
from app.repositories.supabase_client import get_supabase
from app.schemas.analysis import AnalysisResponse, IntakeExtractie

logger = logging.getLogger(__name__)

# Development-only fallback store, keyed by analysis_id.
_memory_store: dict[str, AnalysisResponse] = {}


def save_analysis(
    transcript_id: str,
    opdracht_samenvatting: IntakeExtractie,
    job_id: str | None = None,
) -> AnalysisResponse:
    """Persist an analysis and return it with its generated id."""
    analysis_id = str(uuid.uuid4())
    settings = get_settings()

    if settings.supabase_enabled:
        row = {
            "id": analysis_id,
            "job_id": job_id,
            "transcript_id": transcript_id,
            "opdracht_samenvatting": opdracht_samenvatting.model_dump(),
        }
        get_supabase().table("analyses").insert(row).execute()
    else:
        logger.warning(
            "Supabase not configured — storing analysis %s in memory only.",
            analysis_id,
        )

    result = AnalysisResponse(
        analysis_id=analysis_id,
        transcript_id=transcript_id,
        opdracht_samenvatting=opdracht_samenvatting,
    )

    if not settings.supabase_enabled:
        _memory_store[analysis_id] = result

    return result
