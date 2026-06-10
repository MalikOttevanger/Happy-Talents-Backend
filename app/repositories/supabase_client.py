"""Lazily-created Supabase client, shared across repositories."""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """Return a cached Supabase client built from the service-role key.

    The service-role key bypasses RLS, so this client must only ever be used
    server-side. Callers should check `settings.supabase_enabled` first.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
