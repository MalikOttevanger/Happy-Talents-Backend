"""Matching endpoint — `feature/top3-matching`.

Implements `POST /api/v1/matches` from API.md (§3): take a stored analysis, run the
retrieve-then-rank matching against the interimmer pool, store the shortlist and
return it. The (two) LLM calls are synchronous and run in a threadpool.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.repositories import analyses as analysis_repo
from app.repositories import matches as match_repo
from app.repositories import transcripts as transcript_repo
from app.schemas.matching import MatchCreateRequest, MatchResponse
from app.services.matching import MatchProviderError, MatchValidationError, match

router = APIRouter(prefix="/api/v1", tags=["matches"])


@router.post(
    "/matches",
    response_model=MatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_match(payload: MatchCreateRequest) -> MatchResponse:
    """Rank candidates for an analysis and persist the shortlist.

    Returns 404 when the analysis is unknown, 422 on invalid LLM output and 502
    when the provider fails.
    """
    analysis = analysis_repo.get_analysis(payload.analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis not found: {payload.analysis_id}",
        )

    # The transcript gives the ranking step extra context (same as the n8n flow).
    transcript_text = transcript_repo.get_transcript_text(analysis.transcript_id) or ""

    try:
        result = await run_in_threadpool(
            match,
            analysis.opdracht_samenvatting.opdracht,
            transcript_text,
            payload.limit,
        )
    except MatchValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except MatchProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return match_repo.save_match(
        analysis_id=payload.analysis_id,
        shortlist=result.shortlist,
        aanbeveling=result.aanbeveling,
    )
