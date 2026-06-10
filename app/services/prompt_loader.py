"""Loader for the external YAML prompts under `prompts/`.

Keeps prompts out of the code so they can be tweaked without a deploy. Each YAML
file holds one prompt; see `prompts/intake_analysis.yaml` for the format.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Template
from pydantic import BaseModel

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class Prompt(BaseModel):
    """A single prompt definition loaded from a YAML file."""

    version: int
    model: str
    temperature: float = 0.2
    system: str
    user_template: str

    def render_user(self, **variables) -> str:
        """Render `user_template` (Jinja2) with the given variables."""
        return Template(self.user_template).render(**variables)


@lru_cache
def load_prompt(name: str) -> Prompt:
    """Load and validate the prompt named `name` (without `.yaml`).

    Cached per process; prompts are static config. Raises FileNotFoundError when
    the file is missing.
    """
    path = PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Prompt(**data)
