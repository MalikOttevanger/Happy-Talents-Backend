"""Tests for the AI analysis endpoint and prompt loader."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import transcripts as transcript_repo
from app.schemas.analysis import IntakeExtractie, Opdracht
from app.services.analysis import AnalysisProviderError
from app.services.prompt_loader import load_prompt

client = TestClient(app)

SAMENVATTING = IntakeExtractie(
    opdracht=Opdracht(
        functietitel="Finance Manager",
        klant_pijnpunten="Maandrapportages lopen achter.",
        vereiste_skills=["Finance Management", "SAP"],
        locatie="Amsterdam",
        tarief_min=100,
        tarief_max=120,
        max_reistijd_bucket="30-45",
        urgentie="hoog",
    ),
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
    samenvatting = body["opdracht_samenvatting"]
    assert samenvatting["opdracht"]["functietitel"] == "Finance Manager"
    assert samenvatting["opdracht"]["vereiste_skills"] == ["Finance Management", "SAP"]
    assert samenvatting["opdracht"]["urgentie"] == "hoog"


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
