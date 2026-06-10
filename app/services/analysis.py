"""AI analysis of an intake transcript via OpenAI.

Extracts the client need + competence profile (`OpdrachtSamenvatting`) from a
transcript using OpenAI Structured Outputs, so the model is guaranteed to return
the exact schema. The prompt lives in `prompts/intake_analysis.yaml`.

Note: the technical plan mentions Claude as the LLM provider; per current
direction this endpoint uses OpenAI instead.
"""

import logging

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.analysis import IntakeExtractie
from app.services.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

PROMPT_NAME = "intake_analysis"


class AnalysisProviderError(Exception):
    """The LLM provider failed or refused (maps to HTTP 502)."""


class AnalysisValidationError(Exception):
    """The LLM returned data that does not satisfy the schema (maps to HTTP 422)."""


def _client() -> OpenAI:
    """Build an OpenAI client from configured credentials."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise AnalysisProviderError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=settings.openai_api_key)


def analyse_transcript(transcript_text: str) -> IntakeExtractie:
    """Run the analysis prompt over `transcript_text` and return the structured result.

    Raises AnalysisProviderError on provider failure/refusal and
    AnalysisValidationError when the output cannot be validated.
    """
    settings = get_settings()
    prompt = load_prompt(PROMPT_NAME)
    model = prompt.model or settings.openai_model

    try:
        completion = _client().chat.completions.parse(
            model=model,
            temperature=prompt.temperature,
            messages=[
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.render_user(transcript=transcript_text)},
            ],
            response_format=IntakeExtractie,
        )
    except ValidationError as exc:
        logger.error("Analysis output failed schema validation: %s", exc)
        raise AnalysisValidationError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surfaced as a provider error
        logger.error("OpenAI analysis call failed: %s", exc)
        raise AnalysisProviderError(str(exc)) from exc

    message = completion.choices[0].message
    if message.parsed is None:
        # A refusal (or empty parse) means we have no usable structured data.
        raise AnalysisProviderError(message.refusal or "OpenAI returned no parsed output.")

    return message.parsed
