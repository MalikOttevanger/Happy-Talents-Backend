"""Persistence for match results.

The database design (DATABASE.md) stores a shortlist as `job_candidates` rows
linked to a job. The standalone `POST /api/v1/matches` endpoint runs before a job
linkage exists, so for now the result is kept in a process-local store and gets an
id. The pipeline orchestrator will later persist the shortlist into
`job_candidates`.
"""

import uuid

from app.schemas.matching import Candidate, MatchResponse

# Process-local store, keyed by match_id.
_memory_store: dict[str, MatchResponse] = {}


def save_match(
    analysis_id: str,
    shortlist: list[Candidate],
    aanbeveling: str,
) -> MatchResponse:
    """Persist a match result and return it with its generated id."""
    match_id = str(uuid.uuid4())
    result = MatchResponse(
        match_id=match_id,
        analysis_id=analysis_id,
        shortlist=shortlist,
        aanbeveling=aanbeveling,
    )
    _memory_store[match_id] = result
    return result


def get_match(match_id: str) -> MatchResponse | None:
    """Return the stored match for `match_id`, or None if missing."""
    return _memory_store.get(match_id)
