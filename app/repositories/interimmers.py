"""Read access to the interimmer (expert) pool used for matching.

Reads from the Supabase `interimmers` table (synced from Active Campaign). When
Supabase is not configured the pool is empty — there is no hardcoded mock data in
the application; sample data lives only in tests.

The matching flow (API.md §3) needs two reads: the set of roles that exist (to
constrain the LLM's hard filter) and the candidates for the chosen role.
"""

import logging

from app.core.config import get_settings
from app.repositories.supabase_client import get_supabase
from app.schemas.interimmer import Interimmer

logger = logging.getLogger(__name__)


def _all() -> list[Interimmer]:
    """Return every interimmer (internal helper)."""
    settings = get_settings()
    if not settings.supabase_enabled:
        logger.warning("Supabase not configured — interimmer pool is empty.")
        return []

    response = get_supabase().table("interimmers").select("*").execute()
    return [Interimmer(**row) for row in (response.data or [])]


def get_distinct_roles() -> list[str]:
    """Return the distinct `type_rol` values across all interimmers.

    This is the allowed set the role-selection LLM must choose from, so the chosen
    role always exists and the retrieve step can never be empty.
    """
    roles: set[str] = set()
    for interimmer in _all():
        roles.update(interimmer.type_rol)
    return sorted(roles)


def get_by_role(role: str) -> list[Interimmer]:
    """Return all interimmers whose `type_rol` contains `role`.

    Uses a parameterized Supabase query (the backend builds it — the LLM never
    writes SQL). Falls back to in-memory filtering when Supabase is disabled.
    """
    settings = get_settings()
    if not settings.supabase_enabled:
        return []

    response = (
        get_supabase()
        .table("interimmers")
        .select("*")
        .contains("type_rol", [role])
        .execute()
    )
    return [Interimmer(**row) for row in (response.data or [])]
