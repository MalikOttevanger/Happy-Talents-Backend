"""Gmail endpoints — `feature/gmail-draft` (signature + draft creation).

Implements `GET /api/v1/users/me/signature` (API.md §5) and
`POST /api/v1/gmail/drafts` (API.md §4). Test-phase auth: a single manual refresh
token from `.env` (no per-user SSO yet). The draft body gets the live Gmail
signature appended before it is created.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.repositories import proposals as proposal_repo
from app.schemas.gmail import GmailDraftCreateRequest, GmailDraftResponse, SignatureResponse
from app.services import gmail

router = APIRouter(prefix="/api/v1", tags=["gmail"])


@router.get("/users/me/signature", response_model=SignatureResponse)
async def read_signature() -> SignatureResponse:
    """Read the logged-in user's signature live from Gmail."""
    try:
        signature_html = await run_in_threadpool(gmail.get_signature)
    except gmail.GmailError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return SignatureResponse(signature_html=signature_html)


@router.post(
    "/gmail/drafts",
    response_model=GmailDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gmail_draft(payload: GmailDraftCreateRequest) -> GmailDraftResponse:
    """Create a Gmail draft for a proposal, with the signature appended.

    Returns 404 when the proposal is unknown and 502 when Gmail fails.
    """
    # When a proposal_id is given it must exist (the draft id is stored on it).
    # The frontend may also send an edited email without a stored proposal.
    if payload.proposal_id is not None and proposal_repo.get_proposal(payload.proposal_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal not found: {payload.proposal_id}",
        )

    try:
        signature_html = await run_in_threadpool(gmail.get_signature)
        body_with_signature = payload.body_html
        if signature_html:
            body_with_signature += f"<br/><br/>{signature_html}"
        draft_id = await run_in_threadpool(
            gmail.create_draft, payload.to, payload.subject, body_with_signature
        )
    except gmail.GmailError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if payload.proposal_id is not None:
        proposal_repo.set_gmail_draft_id(payload.proposal_id, draft_id)
    return GmailDraftResponse(gmail_draft_id=draft_id)
