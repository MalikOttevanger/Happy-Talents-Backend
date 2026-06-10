"""Top-3 matching via OpenAI — retrieve-then-rank (API.md §3).

Three steps:
  1. Role selection (LLM): pick the best-fitting `type_rol` from the roles that
     actually exist in the database (the backend supplies the allowed set). The
     LLM returns only a chosen role value, never SQL.
  2. Retrieve (backend): validate the chosen role and run a parameterized query on
     `type_rol` — the single hard filter, so the result is never empty.
  3. Rank (LLM): score the retrieved group on soft criteria (skill depth, rate,
     location, hours) into a top-N.

Prompts live in `prompts/role_selection.yaml` and `prompts/top3_ranking.yaml`.
"""

import json
import logging

from openai import OpenAI

from app.core.config import get_settings
from app.repositories import interimmers as interimmer_repo
from app.schemas.analysis import Opdracht
from app.schemas.matching import MatchResult, RoleSelection
from app.services.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

ROLE_PROMPT = "role_selection"
RANK_PROMPT = "top3_ranking"


class MatchProviderError(Exception):
    """The LLM provider failed or refused (maps to HTTP 502)."""


class MatchValidationError(Exception):
    """The LLM returned data that does not satisfy the schema (maps to HTTP 422)."""


def _client() -> OpenAI:
    """Build an OpenAI client from configured credentials."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise MatchProviderError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=settings.openai_api_key)


def _select_role(opdracht: Opdracht, allowed_roles: list[str]) -> str:
    """Step 1: let the LLM pick one role from the allowed set, then validate it."""
    prompt = load_prompt(ROLE_PROMPT)
    settings = get_settings()
    user_message = prompt.render_user(
        opdracht=opdracht.model_dump_json(),
        allowed_roles=json.dumps(allowed_roles, ensure_ascii=False),
    )

    try:
        completion = _client().chat.completions.parse(
            model=prompt.model or settings.openai_model,
            temperature=prompt.temperature,
            messages=[
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": user_message},
            ],
            response_format=RoleSelection,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a provider error
        logger.error("OpenAI role-selection call failed: %s", exc)
        raise MatchProviderError(str(exc)) from exc

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise MatchProviderError("OpenAI returned no role selection.")

    # The backend never trusts the LLM blindly: the role must exist.
    if parsed.gekozen_rol not in allowed_roles:
        raise MatchValidationError(
            f"LLM chose a role outside the allowed set: {parsed.gekozen_rol!r}"
        )
    return parsed.gekozen_rol


def _rank(opdracht: Opdracht, candidates: list, transcript_text: str, limit: int) -> MatchResult:
    """Step 3: rank the retrieved candidates on soft criteria into a top-`limit`."""
    prompt = load_prompt(RANK_PROMPT)
    settings = get_settings()
    candidates_json = json.dumps([c.model_dump() for c in candidates], ensure_ascii=False)
    user_message = prompt.render_user(
        opdracht=opdracht.model_dump_json(),
        candidates=candidates_json,
        transcript=transcript_text,
    )

    try:
        completion = _client().chat.completions.parse(
            model=prompt.model or settings.openai_model,
            temperature=prompt.temperature,
            messages=[
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": user_message},
            ],
            response_format=MatchResult,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a provider error
        logger.error("OpenAI ranking call failed: %s", exc)
        raise MatchProviderError(str(exc)) from exc

    result = completion.choices[0].message.parsed
    if result is None:
        raise MatchProviderError("OpenAI returned no ranking output.")

    result.shortlist = result.shortlist[:limit]
    return result


def match(opdracht: Opdracht, transcript_text: str, limit: int = 3) -> MatchResult:
    """Run the full retrieve-then-rank flow and return the ranked shortlist.

    With no interimmers (and therefore no roles) there is nothing to match, so we
    return a clear, empty result without calling the LLM.
    """
    allowed_roles = interimmer_repo.get_distinct_roles()
    if not allowed_roles:
        return MatchResult(
            shortlist=[],
            aanbeveling="Geen interimmers beschikbaar om te matchen.",
        )

    chosen_role = _select_role(opdracht, allowed_roles)
    candidates = interimmer_repo.get_by_role(chosen_role)
    logger.info("Matching: chosen role %r → %d candidate(s).", chosen_role, len(candidates))

    return _rank(opdracht, candidates, transcript_text, limit)
