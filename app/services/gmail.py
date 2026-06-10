"""Gmail integration via the REST API.

Test-phase setup: a single manually-generated refresh token (from `.env`) is
exchanged for a short-lived access token, which is used to read the signature and
create drafts. Later this is replaced by per-user tokens from the SSO flow. Uses
httpx directly to keep dependencies light.

Scopes required on the refresh token:
  - https://www.googleapis.com/auth/gmail.compose        (create drafts)
  - https://www.googleapis.com/auth/gmail.settings.basic (read signature)
"""

import base64
import logging
from email.message import EmailMessage

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailError(Exception):
    """Gmail is not configured or the API call failed (maps to HTTP 502)."""


def _access_token() -> str:
    """Exchange the configured refresh token for a short-lived access token."""
    settings = get_settings()
    if not settings.gmail_enabled:
        raise GmailError("Google/Gmail credentials are not configured.")

    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.google_refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    if response.status_code != 200:
        raise GmailError(f"Token refresh failed ({response.status_code}): {response.text}")
    return response.json()["access_token"]


def get_signature() -> str:
    """Return the HTML signature of the primary send-as address (empty if none)."""
    token = _access_token()
    response = httpx.get(
        f"{GMAIL_BASE}/settings/sendAs",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if response.status_code != 200:
        raise GmailError(f"Reading signature failed ({response.status_code}): {response.text}")

    send_as = response.json().get("sendAs", [])
    primary = next((s for s in send_as if s.get("isPrimary")), None) or (send_as[0] if send_as else {})
    return primary.get("signature", "") or ""


def _build_raw_message(to: str, subject: str, body_html: str) -> str:
    """Build a base64url-encoded RFC822 HTML message for the Gmail API."""
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    # Plain-text fallback keeps the message well-formed; HTML is the main part.
    message.set_content("Bekijk dit voorstel in een HTML-compatibele client.")
    message.add_alternative(body_html, subtype="html")
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def create_draft(to: str, subject: str, body_html: str) -> str:
    """Create a Gmail draft and return its id.

    The caller is responsible for having appended the signature to `body_html`.
    """
    token = _access_token()
    raw = _build_raw_message(to, subject, body_html)
    response = httpx.post(
        f"{GMAIL_BASE}/drafts",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": {"raw": raw}},
        timeout=15,
    )
    if response.status_code not in (200, 201):
        raise GmailError(f"Creating draft failed ({response.status_code}): {response.text}")
    return response.json()["id"]
