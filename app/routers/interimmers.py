"""Interimmers endpoint — read access to the candidate pool.

`GET /api/v1/interimmers` returns the full interimmer pool (from Supabase, or the
development seed when Supabase is not configured). The frontend candidate sheet
reads from here so it shows the same data the matching step runs against.
"""

from fastapi import APIRouter

from app.repositories import interimmers as interimmer_repo
from app.schemas.interimmer import Interimmer

router = APIRouter(prefix="/api/v1", tags=["interimmers"])


@router.get("/interimmers", response_model=list[Interimmer])
async def list_interimmers() -> list[Interimmer]:
    """Return every interimmer available for matching."""
    return interimmer_repo.get_all()
