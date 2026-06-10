"""Tests for the AI analysis endpoint and prompt loader."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import transcripts as transcript_repo
from app.schemas.analysis import OpdrachtSamenvatting
from app.services.analysis import AnalysisProviderError
from app.services.prompt_loader import load_prompt

client = TestClient(app)

SAMENVATTING = OpdrachtSamenvatting(
    klant_pijnpunten="Maandrapportages lopen achter.",
    gevraagde_competenties=["Finance Management", "SAP"],
    specialisme="Finance Manager",
    locatie_opdracht="Amsterdam",
    budget_uur=120,
)


def _store_transcript() -> str:
    """Persist a transcript via the repo and return its id."""
    stored = transcript_repo.save_transcript(
        text="[00:00] Klant: We zoeken een interim finance manager in Amsterdam.",
        segments_dump=[],
        source_url="https://web.plaud.ai/s/test",
        duration_seconds=120,
    )
    return stored.transcript_id


def test_prompt_loader_reads_intake_analysis():
    prompt = load_prompt("intake_analysis")
    assert prompt.version >= 1
    assert "transcript" in prompt.user_template
    rendered = prompt.render_user(transcript="HELLO")
    assert "HELLO" in rendered


def test_create_analysis_returns_201_with_summary():
    transcript_id = _store_transcript()
    with patch("app.routers.analyses.analyse_transcript", return_value=SAMENVATTING):
        response = client.post("/api/v1/analyses", json={"transcript_id": transcript_id})

    assert response.status_code == 201
    body = response.json()
    assert body["transcript_id"] == transcript_id
    assert body["analysis_id"]
    assert body["opdracht_samenvatting"]["specialisme"] == "Finance Manager"
    assert body["opdracht_samenvatting"]["gevraagde_competenties"] == ["Finance Management", "SAP"]


def test_create_analysis_unknown_transcript_returns_404():
    with patch("app.routers.analyses.analyse_transcript", return_value=SAMENVATTING):
        response = client.post("/api/v1/analyses", json={"transcript_id": "does-not-exist"})
    assert response.status_code == 404


def test_create_analysis_provider_error_returns_502():
    transcript_id = _store_transcript()
    with patch(
        "app.routers.analyses.analyse_transcript",
        side_effect=AnalysisProviderError("boom"),
    ):
        response = client.post("/api/v1/analyses", json={"transcript_id": transcript_id})
    assert response.status_code == 502
