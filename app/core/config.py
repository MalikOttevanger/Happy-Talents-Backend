"""Application configuration, loaded from environment variables / `.env`."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Values are read from environment variables, falling back to a local `.env`
    file. See `.env.example` for the full list and explanations.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase persistence. When either value is missing, the repositories fall
    # back to an in-memory store so endpoints stay usable in development.
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # OpenAI (AI analysis).
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-2024-08-06"

    # Plaud scraping (Selenium / Chromium).
    chromium_path: str = ""
    chromedriver_path: str = ""
    plaud_page_timeout: int = 20

    @property
    def supabase_enabled(self) -> bool:
        """True when both Supabase credentials are configured."""
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
