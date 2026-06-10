"""Request/response models for the proposal endpoint.

Implements `POST /api/v1/proposals` (API.md §4). The email is hybrid: an
LLM-written intro (opening + "Behoefte" section) plus a fixed template assembled by
the backend (candidate blocks, rate paragraph, sign-off).

`klant_naam` and `klant_bedrijf` are supplied by the frontend at intake time. They
are not in the API.md request example (there they come from the job); they are
added here so the standalone endpoint works before the orchestrator/jobs exist.
"""

from pydantic import BaseModel, Field


class EmailIntro(BaseModel):
    """Structured LLM output: the email opening up to and including 'Behoefte'."""

    email_intro: str = Field(description="HTML string for the intro section.")


class ProposalCreateRequest(BaseModel):
    """Body for `POST /api/v1/proposals`."""

    match_id: str = Field(description="Id of a stored match.")
    klant_naam: str = Field(description="Client contact name (first name is greeted).")
    klant_bedrijf: str = Field(description="Client company name.")
    selected_candidate_ids: list[str] | None = Field(
        default=None,
        description="Candidate ids to include; when omitted, the whole shortlist is used.",
    )


class ProposalResponse(BaseModel):
    """Generated proposal email."""

    proposal_id: str
    subject: str
    body_html: str
