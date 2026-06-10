"""Request/response models for the AI analysis endpoint.

Implements `POST /api/v1/analyses` (API.md §2). The extracted structure is the
nested `klant` + `opdracht` shape defined for the OpenAI extraction prompt; it is
stored in the `analyses.opdracht_samenvatting` jsonb column.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Fixed travel-time buckets used across the app.
ReistijdBucket = Literal["0-30", "30-45", "45-60", "60+"]
Urgentie = Literal["hoog", "midden", "laag"]


class Opdracht(BaseModel):
    """The assignment: role, requirements, terms and context."""

    functietitel: str | None = None
    omschrijving: str | None = None
    klant_pijnpunten: str | None = Field(
        default=None,
        description="Eén zin: welke problemen/frustraties veroorzaken deze opdracht.",
    )
    vereiste_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    uren_per_week: int | None = None
    startdatum: str | None = Field(default=None, description="ISO-datum (YYYY-MM-DD).")
    einddatum: str | None = Field(default=None, description="ISO-datum (YYYY-MM-DD).")
    tarief_min: int | None = None
    tarief_max: int | None = None
    locatie: str | None = None
    remote_mogelijk: bool = False
    max_reistijd_bucket: ReistijdBucket | None = None
    sector: str | None = None
    urgentie: Urgentie = "midden"


class IntakeExtractie(BaseModel):
    """Full structured extraction of one intake conversation.

    This is also the schema the LLM must return (OpenAI Structured Outputs), and
    the object stored in `analyses.opdracht_samenvatting`.
    """

    opdracht: Opdracht


class AnalysisCreateRequest(BaseModel):
    """Body for `POST /api/v1/analyses`."""

    transcript_id: str = Field(description="Id of a previously stored transcript.")


class AnalysisResponse(BaseModel):
    """Result of analysing a transcript."""

    analysis_id: str
    transcript_id: str
    opdracht_samenvatting: IntakeExtractie
