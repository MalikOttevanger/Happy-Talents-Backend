"""Plaud transcript scraping.

Plaud has no public read API for share links, so the transcript is scraped from
the public share page with a headless browser. This module is the only place that
knows about the page structure; it returns clean, structured data to the rest of
the app. Adapted from the original `Happy_talents/plaud_scraper.py`.
"""

import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.core.config import get_settings
from app.schemas.transcript import TranscriptSegment

logger = logging.getLogger(__name__)


class PlaudScrapeError(Exception):
    """Raised when a transcript could not be fetched from a Plaud share link."""


def _build_browser() -> webdriver.Chrome:
    """Create a headless Chrome browser.

    Chromium/chromedriver paths come from settings when provided (Docker / Cloud
    Run); when empty, Selenium Manager resolves the driver automatically, which is
    the common case for local development.
    """
    settings = get_settings()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if settings.chromium_path:
        options.binary_location = settings.chromium_path

    service = Service(settings.chromedriver_path) if settings.chromedriver_path else Service()
    return webdriver.Chrome(service=service, options=options)


def _scrape_segments(url: str) -> list[TranscriptSegment]:
    """Open the share page and extract the transcript as ordered segments."""
    settings = get_settings()
    browser = _build_browser()
    wait = WebDriverWait(browser, settings.plaud_page_timeout)

    try:
        browser.get(url)

        # The share content lives inside an iframe.
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        browser.switch_to.frame(iframe)

        # Dismiss the cookie banner if it appears; absence is fine.
        try:
            reject_btn = WebDriverWait(browser, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[normalize-space()='Reject All']")
                )
            )
            reject_btn.click()
        except Exception:
            pass

        transcript_tab = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-testid="share-note-tabs-item-transcript-button"]')
            )
        )
        transcript_tab.click()

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="share-landing-trans-list"] .trans-item')
            )
        )

        rows = browser.find_elements(
            By.CSS_SELECTOR, '[data-testid="share-landing-trans-list"] .trans-item'
        )

        segments: list[TranscriptSegment] = []
        for row in rows:
            timestamp = row.find_element(By.CSS_SELECTOR, ".ttime").text.split("Speaker")[0].strip()
            speaker = row.find_element(By.CSS_SELECTOR, ".sname").text.strip()
            text = row.find_element(By.CSS_SELECTOR, ".tcont").text.strip()
            segments.append(TranscriptSegment(timestamp=timestamp, speaker=speaker, text=text))

        return segments
    finally:
        browser.quit()


def _flatten(segments: list[TranscriptSegment]) -> str:
    """Render segments as a single readable transcript string."""
    return "\n".join(f"[{seg.timestamp}] {seg.speaker}: {seg.text}" for seg in segments)


def _duration_seconds(segments: list[TranscriptSegment]) -> int | None:
    """Derive total duration from the last segment's timestamp.

    Timestamps are "MM:SS" or "HH:MM:SS". Returns None when the last timestamp
    cannot be parsed.
    """
    if not segments:
        return None

    last = segments[-1].timestamp
    parts = last.split(":")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None

    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    if len(numbers) == 3:
        hours, minutes, seconds = numbers
        return hours * 3600 + minutes * 60 + seconds
    return None


def fetch_transcript(plaud_url: str) -> tuple[str, list[TranscriptSegment], int | None]:
    """Fetch a Plaud transcript and return (text, segments, duration_seconds).

    Raises PlaudScrapeError when the page cannot be scraped or contains no
    transcript, so the caller can map it to a clean HTTP error.
    """
    try:
        segments = _scrape_segments(plaud_url)
    except Exception as exc:  # noqa: BLE001 - surfaced as a domain error
        logger.error("Plaud scrape failed for %s: %s", plaud_url, exc)
        raise PlaudScrapeError(f"Could not fetch transcript from Plaud: {exc}") from exc

    if not segments:
        raise PlaudScrapeError("No transcript found on the Plaud share page.")

    return _flatten(segments), segments, _duration_seconds(segments)
