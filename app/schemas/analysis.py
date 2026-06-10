"""Request/response models for the AI analysis endpoint.

Mirrors `POST /api/v1/analyses` in API.md (§2) and `OpdrachtSamenvatting` in the
frontend `types.ts`.
"""

from pydantic import BaseModel, Field


class OpdrachtSamenvatting(BaseModel):
    """Structured client need + competence profile extracted from a transcript.

    This is also the schema the LLM must return. Fields that the transcript does
    not mention are null (or an empty list), never invented.
    """

    klant_pijnpunten: str | None = Field(
        default=None, description="Wat is het probleem/de aanleiding van de klant?"
    )
    gevraagde_competenties: list[str] = Field(
        default_factory=list, description="Gevraagde skills/competenties."
    )
    specialisme: str | None = Field(default=None, description="Functie/rol, bv. 'Finance Manager'.")
    sector_ervaring: list[str] = Field(
        default_factory=list, description="Relevante sectoren, bv. ['Retail']."
    )
    locatie_opdracht: str | None = Field(default=None, description="Locatie van de opdracht.")
    reistijd_voorkeur_minuten: int | None = Field(
        default=None, description="Maximale reistijd in minuten."
    )
    startdatum: str | None = Field(default=None, description="Gewenste startdatum (ISO of tekst).")
    contractvorm: str | None = Field(default=None, description="Bv. 'Interim', 'Detachering'.")
    budget_uur: int | None = Field(default=None, description="Budget per uur in euro's.")
    duur_opdracht: str | None = Field(default=None, description="Verwachte duur, bv. '6 maanden'.")
    bijzonderheden: str | None = Field(default=None, description="Overige relevante punten.")
    persoonlijke_context: str | None = Field(
        default=None, description="Persoonlijke context van de klant/opdracht."
    )


class AnalysisCreateRequest(BaseModel):
    """Body for `POST /api/v1/analyses`."""

    transcript_id: str = Field(description="Id of a previously stored transcript.")


class AnalysisResponse(BaseModel):
    """Result of analysing a transcript."""

    analysis_id: str
    transcript_id: str
    opdracht_samenvatting: OpdrachtSamenvatting
