"""Sample interimmer data for tests and live checks.

Derived from the original n8n mock pool, kept ONLY as test data and aligned to the
DATABASE.md `interimmers` shape (single `naam`, integer `uurtarief`, `skills`).
The application reads real interimmers from the repository, never from here.
"""

from app.schemas.interimmer import Interimmer

SAMPLE_EXPERTS: list[Interimmer] = [
    Interimmer(
        id="exp_001", naam="Piet Rijlaarsdam", type_rol=["Content Marketeer"],
        skills=["Creative copywriting", "Content"], max_reistijd="60 minuten",
        provincie="Noord-Holland", uurtarief=85, uren_beschikbaar="16 uur",
        werklocatie="Maakt niet uit",
    ),
    Interimmer(
        id="exp_002", naam="Henk van der Made",
        type_rol=["Online Marketeer", "Content Marketeer", "Marketing Manager",
                  "Social Media Advertising specialist"],
        skills=["Campagne management", "Social media"], max_reistijd="Maakt niet uit",
        provincie="Noord-Brabant", uurtarief=85, uren_beschikbaar="32 uur",
        werklocatie="Hybride",
    ),
    Interimmer(
        id="exp_007", naam="Merijn van Maarseveen",
        type_rol=["Content Marketeer", "Communicatie adviseur", "Interim Strateeg"],
        skills=["Creatieve strategie", "Merkstrategie"], max_reistijd="60 minuten",
        provincie="Zuid-Holland", uurtarief=110, uren_beschikbaar="32 uur",
        werklocatie="Maakt niet uit",
    ),
    Interimmer(
        id="exp_014", naam="Niek Pijpers", type_rol=["Content Marketeer"],
        skills=["Content"], max_reistijd="60 minuten", provincie="Gelderland",
        uurtarief=75, uren_beschikbaar="16 uur", werklocatie="Maakt niet uit",
    ),
    Interimmer(
        id="exp_018", naam="Gerrit van Oene",
        type_rol=["Online Marketeer", "Content Marketeer"],
        skills=["Content management"], max_reistijd="60 minuten",
        provincie="Noord-Holland", uurtarief=65, uren_beschikbaar="40 uur",
        werklocatie="Hybride",
    ),
    Interimmer(
        id="exp_013", naam="Jaap Werker",
        type_rol=["Performance Marketeer", "Marketing Lead", "SEA specialist"],
        skills=["SEA", "Performance"], max_reistijd="30 minuten", provincie="Drenthe",
        uurtarief=95, uren_beschikbaar="8 uur", werklocatie="Remote",
    ),
]


def roles_in(experts: list[Interimmer]) -> list[str]:
    """Distinct roles across a list of experts (mirrors the repo helper)."""
    roles: set[str] = set()
    for expert in experts:
        roles.update(expert.type_rol)
    return sorted(roles)


def experts_with_role(experts: list[Interimmer], role: str) -> list[Interimmer]:
    """Filter experts whose type_rol contains `role`."""
    return [e for e in experts if role in e.type_rol]
