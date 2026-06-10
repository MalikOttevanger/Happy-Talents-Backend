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
    """Return every interimmer (internal helper).

    Falls back to the development seed when Supabase is not configured, so
    matching works locally before the `interimmers` table is provisioned.
    """
    settings = get_settings()
    if not settings.supabase_enabled:
        from app.repositories.dev_interimmers import DEV_INTERIMMERS

        logger.warning(
            "Supabase not configured — using the development interimmer seed (%d).",
            len(DEV_INTERIMMERS),
        )
        return DEV_INTERIMMERS

    response = get_supabase().table("interimmers").select("*").execute()
    return [Interimmer(**row) for row in (response.data or [])]


def get_all() -> list[Interimmer]:
    """Return every interimmer (public accessor for the read endpoint)."""
    return _all()


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
        return [i for i in _all() if role in i.type_rol]

    response = (
        get_supabase()
        .table("interimmers")
        .select("*")
        .contains("type_rol", [role])
        .execute()
    )
    return [Interimmer(**row) for row in (response.data or [])]
