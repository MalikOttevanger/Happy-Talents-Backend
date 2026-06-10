"""Request/response models for the top-3 matching endpoint.

Implements `POST /api/v1/matches` (API.md §3), retrieve-then-rank with a single
hard filter on `type_rol`. The candidate shape mirrors `Candidate` in the frontend
`types.ts`.
"""

from pydantic import BaseModel, Field


class RoleSelection(BaseModel):
    """Structured LLM output for step 1: the chosen role (hard filter).

    The model must pick `gekozen_rol` from the allowed set supplied by the backend
    (the roles that actually exist in the database); the backend validates it.
    """

    gekozen_rol: str = Field(description="Best-fitting role, chosen from the allowed list.")


class Candidate(BaseModel):
    """A ranked candidate in the shortlist.

    `id` is assigned by the backend when the match is stored (the LLM does not set
    it); the proposals endpoint selects candidates by this id.
    """

    id: str | None = None
    naam: str
    matchscore: int | None = Field(default=None, description="0-100, no decimals.")
    matchuitleg: str
    aandachtspunten: str | None = None
    beschikbaarheid: str
    uurtarief: int | str
    startdatum: str | None = None
    specialisme: str | None = None
    locatie: str | None = None
    competenties: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    """Structured LLM output for step 3: the ranked shortlist plus a recommendation."""

    shortlist: list[Candidate] = Field(default_factory=list)
    aanbeveling: str


class MatchCreateRequest(BaseModel):
    """Body for `POST /api/v1/matches`."""

    analysis_id: str = Field(description="Id of a previously stored analysis.")
    limit: int = Field(default=3, ge=1, le=10, description="Max candidates in the shortlist.")


class MatchResponse(BaseModel):
    """Result of matching: a ranked shortlist with explanations."""

    match_id: str
    analysis_id: str
    shortlist: list[Candidate]
    aanbeveling: str
