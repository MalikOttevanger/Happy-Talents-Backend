"""Proposal email intro generation via OpenAI.

Generates the LLM-written opening (greeting + thank-you + hand-out link +
"Behoefte" bullets). The fixed remainder of the email is assembled by
`app.services.email_template`. Prompt lives in `prompts/proposal_intro.yaml`.
"""

import logging

from openai import OpenAI

from app.core.config import get_settings
from app.schemas.analysis import Opdracht
from app.schemas.proposal import EmailIntro
from app.services.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

PROMPT_NAME = "proposal_intro"


class ProposalProviderError(Exception):
    """The LLM provider failed or refused (maps to HTTP 502)."""


def _client() -> OpenAI:
    """Build an OpenAI client from configured credentials."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise ProposalProviderError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=settings.openai_api_key)


def generate_intro(
    voornaam: str,
    bedrijf: str,
    opdracht: Opdracht,
    transcript_text: str,
) -> str:
    """Generate the HTML intro for the proposal email.

    Raises ProposalProviderError on provider failure/refusal.
    """
    settings = get_settings()
    prompt = load_prompt(PROMPT_NAME)
    user_message = prompt.render_user(
        voornaam=voornaam,
        bedrijf=bedrijf,
        opdracht=opdracht.model_dump_json(),
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
            response_format=EmailIntro,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a provider error
        logger.error("OpenAI proposal-intro call failed: %s", exc)
        raise ProposalProviderError(str(exc)) from exc

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ProposalProviderError(
            completion.choices[0].message.refusal or "OpenAI returned no intro."
        )

    return parsed.email_intro
