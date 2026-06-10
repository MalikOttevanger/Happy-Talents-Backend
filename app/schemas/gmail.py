"""Request/response models for the Gmail endpoints (API.md §4–5)."""

from pydantic import BaseModel, Field


class SignatureResponse(BaseModel):
    """The logged-in user's Gmail signature."""

    signature_html: str


class GmailDraftCreateRequest(BaseModel):
    """Body for `POST /api/v1/gmail/drafts`."""

    proposal_id: str | None = Field(
        default=None,
        description="Id of the proposal this draft is for (the draft id is stored on it).",
    )
    to: str = Field(description="Recipient email address.")
    subject: str
    body_html: str = Field(description="Email body; the signature is appended by the backend.")


class GmailDraftResponse(BaseModel):
    """The created Gmail draft."""

    gmail_draft_id: str
