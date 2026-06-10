"""Interimmer (expert) model used by the matching step.

Fields follow the `interimmers` table in DATABASE.md (synced from Active Campaign).
`type_rol` is the single hard filter during matching; the other fields are scored.
"""

from pydantic import BaseModel, Field


class Interimmer(BaseModel):
    """A single interim professional available for matching."""

    id: str
    ac_contact_id: str | None = None
    naam: str | None = None
    email: str | None = None
    telefoon: str | None = None
    type_rol: list[str] = Field(default_factory=list, description="Roles (hard filter).")
    provincie: str | None = None
    uurtarief: int | None = Field(default=None, description="Hourly rate in euros.")
    uren_beschikbaar: str | None = Field(default=None, description="e.g. '32 uur'.")
    werklocatie: str | None = None
    max_reistijd: str | None = None
    skills: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
