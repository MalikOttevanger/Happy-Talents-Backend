"""AI analysis endpoint — `feature/ai-analysis`.

Implements `POST /api/v1/analyses` from API.md (§2): take a stored transcript,
extract the client need + competence profile via OpenAI, store it, and return it.
The OpenAI call is synchronous and runs in a threadpool to avoid blocking.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.repositories import analyses as analysis_repo
from app.repositories import transcripts as transcript_repo
from app.schemas.analysis import AnalysisCreateRequest, AnalysisResponse
from app.services.analysis import (
    AnalysisProviderError,
    AnalysisValidationError,
    analyse_transcript,
)

router = APIRouter(prefix="/api/v1", tags=["analyses"])


@router.post(
    "/analyses",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(payload: AnalysisCreateRequest) -> AnalysisResponse:
    """Analyse a transcript and persist the resulting summary.

    Returns 404 when the transcript is unknown, 422 when the LLM output is
    invalid, and 502 when the provider fails.
    """
    transcript_text = transcript_repo.get_transcript_text(payload.transcript_id)
    if transcript_text is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript not found: {payload.transcript_id}",
        )

    try:
        opdracht_samenvatting = await run_in_threadpool(analyse_transcript, transcript_text)
    except AnalysisValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except AnalysisProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return analysis_repo.save_analysis(
        transcript_id=payload.transcript_id,
        opdracht_samenvatting=opdracht_samenvatting,
    )
