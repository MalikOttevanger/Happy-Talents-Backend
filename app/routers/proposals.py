"""Proposal endpoint — `feature/gmail-draft`.

Implements `POST /api/v1/proposals` from API.md (§4): generate the proposal email
for the selected candidates of a match. Hybrid generation — an LLM-written intro
plus the fixed template. The Gmail-draft step (`POST /api/v1/gmail/drafts`) is a
separate endpoint added once Google OAuth2 is in place.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.repositories import analyses as analysis_repo
from app.repositories import matches as match_repo
from app.repositories import proposals as proposal_repo
from app.repositories import transcripts as transcript_repo
from app.schemas.proposal import ProposalCreateRequest, ProposalResponse
from app.services.email_template import build_proposal_email
from app.services.proposal_intro import ProposalProviderError, generate_intro

router = APIRouter(prefix="/api/v1", tags=["proposals"])


@router.post(
    "/proposals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_proposal(payload: ProposalCreateRequest) -> ProposalResponse:
    """Generate and persist the proposal email for the selected candidates.

    Returns 404 when the match/analysis is unknown, 400 when no candidates are
    selected, and 502 when the LLM provider fails.
    """
    match = match_repo.get_match(payload.match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match not found: {payload.match_id}",
        )

    # Select the requested candidates, or the whole shortlist when none specified.
    if payload.selected_candidate_ids:
        wanted = set(payload.selected_candidate_ids)
        candidates = [c for c in match.shortlist if c.id in wanted]
    else:
        candidates = list(match.shortlist)

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidates selected for the proposal.",
        )

    analysis = analysis_repo.get_analysis(match.analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis not found: {match.analysis_id}",
        )

    opdracht = analysis.opdracht_samenvatting.opdracht
    transcript_text = transcript_repo.get_transcript_text(analysis.transcript_id) or ""
    voornaam = payload.klant_naam.strip().split()[0] if payload.klant_naam.strip() else payload.klant_naam

    try:
        intro_html = await run_in_threadpool(
            generate_intro, voornaam, payload.klant_bedrijf, opdracht, transcript_text
        )
    except ProposalProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    subject, body_html = build_proposal_email(
        intro_html=intro_html,
        candidates=candidates,
        klant_naam=payload.klant_naam,
        klant_bedrijf=payload.klant_bedrijf,
        opdracht=opdracht,
    )

    return proposal_repo.save_proposal(subject=subject, body_html=body_html)
