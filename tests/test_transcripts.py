"""Tests for the transcript endpoint and Plaud helpers."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.transcript import TranscriptSegment
from app.services.plaud import PlaudScrapeError, _duration_seconds, _flatten

client = TestClient(app)

SEGMENTS = [
    TranscriptSegment(timestamp="00:00", speaker="Robert", text="Welkom."),
    TranscriptSegment(timestamp="02:15", speaker="Klant", text="We zoeken finance."),
]


def test_flatten_renders_readable_lines():
    assert _flatten(SEGMENTS) == "[00:00] Robert: Welkom.\n[02:15] Klant: We zoeken finance."


def test_duration_parses_mm_ss():
    assert _duration_seconds(SEGMENTS) == 135


def test_duration_parses_hh_mm_ss():
    segs = [TranscriptSegment(timestamp="1:00:10", speaker="A", text="x")]
    assert _duration_seconds(segs) == 3610


def test_duration_returns_none_for_unparseable():
    segs = [TranscriptSegment(timestamp="onbekend", speaker="A", text="x")]
    assert _duration_seconds(segs) is None


def test_create_transcript_returns_201_with_payload():
    fake = (_flatten(SEGMENTS), SEGMENTS, _duration_seconds(SEGMENTS))
    with patch("app.routers.transcripts.fetch_transcript", return_value=fake):
        response = client.post(
            "/api/v1/transcripts",
            json={"plaud_url": "https://app.plaud.ai/share/abc123"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["duration_seconds"] == 135
    assert len(body["segments"]) == 2
    assert body["transcript_id"]


def test_create_transcript_maps_scrape_error_to_502():
    with patch(
        "app.routers.transcripts.fetch_transcript",
        side_effect=PlaudScrapeError("boom"),
    ):
        response = client.post(
            "/api/v1/transcripts",
            json={"plaud_url": "https://app.plaud.ai/share/abc123"},
        )

    assert response.status_code == 502


def test_create_transcript_rejects_invalid_url():
    response = client.post("/api/v1/transcripts", json={"plaud_url": "not-a-url"})
    assert response.status_code == 422
