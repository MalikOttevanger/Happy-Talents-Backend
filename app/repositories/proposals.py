"""Persistence for proposals.

Stores proposals in the Supabase `proposals` table when configured, otherwise in a
process-local dict (development fallback). `gmail_draft_id` is filled later by the
Gmail-draft step.
"""

import logging
import uuid

from app.core.config import get_settings
from app.repositories.supabase_client import get_supabase
from app.schemas.proposal import ProposalResponse

logger = logging.getLogger(__name__)

# Development-only fallback store, keyed by proposal_id.
_memory_store: dict[str, ProposalResponse] = {}


def save_proposal(
    subject: str,
    body_html: str,
    job_id: str | None = None,
) -> ProposalResponse:
    """Persist a proposal and return it with its generated id."""
    proposal_id = str(uuid.uuid4())
    settings = get_settings()

    if settings.supabase_enabled:
        row = {
            "id": proposal_id,
            "job_id": job_id,
            "subject": subject,
            "body_html": body_html,
        }
        get_supabase().table("proposals").insert(row).execute()
    else:
        logger.warning(
            "Supabase not configured — storing proposal %s in memory only.",
            proposal_id,
        )

    result = ProposalResponse(proposal_id=proposal_id, subject=subject, body_html=body_html)

    if not settings.supabase_enabled:
        _memory_store[proposal_id] = result

    return result
