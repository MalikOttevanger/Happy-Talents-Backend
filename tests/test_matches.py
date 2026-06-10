"""Tests for the top-3 matching endpoint and service (retrieve-then-rank)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import analyses as analysis_repo
from app.schemas.analysis import IntakeExtractie, Opdracht
from app.schemas.matching import Candidate, MatchResult
from app.services import matching
from app.services.matching import MatchProviderError, MatchValidationError, match

client = TestClient(app)

OPDRACHT = Opdracht(
    functietitel="Content Marketeer",
    vereiste_skills=["Content marketing", "Social media"],
    uren_per_week=24,
    locatie="Rotterdam",
    tarief_min=70,
    tarief_max=80,
    urgentie="hoog",
)

MATCH = MatchResult(
    shortlist=[
        Candidate(
            naam="Niek Pijpers",
            matchscore=82,
            matchuitleg="Content Marketeer met directe rol-fit.",
            beschikbaarheid="16 uur, Maakt niet uit, max 60 minuten reistijd",
            uurtarief=75,
            specialisme="Content Marketeer",
            locatie="Gelderland",
            competenties=["Content marketing"],
        )
    ],
    aanbeveling="Niek is de sterkste op skill-fit.",
)


def _store_analysis() -> str:
    """Store an analysis via the repo and return its id."""
    stored = analysis_repo.save_analysis(
        transcript_id="t-1",
        opdracht_samenvatting=IntakeExtractie(opdracht=OPDRACHT),
    )
    return stored.analysis_id


def test_match_empty_pool_skips_llm():
    with patch.object(matching.interimmer_repo, "get_distinct_roles", return_value=[]):
        result = match(OPDRACHT, "transcript", limit=3)
    assert result.shortlist == []
    assert "Geen interimmers" in result.aanbeveling


def test_select_role_rejects_role_outside_allowed_set():
    bad = matching.RoleSelection(gekozen_rol="Astronaut")
    with patch.object(matching, "_client") as client_mock:
        parsed = client_mock.return_value.chat.completions.parse.return_value
        parsed.choices[0].message.parsed = bad
        try:
            matching._select_role(OPDRACHT, ["Content Marketeer", "Marketing Manager"])
            raise AssertionError("expected MatchValidationError")
        except MatchValidationError:
            pass


def test_match_runs_retrieve_then_rank():
    with patch.object(
        matching.interimmer_repo, "get_distinct_roles", return_value=["Content Marketeer"]
    ), patch.object(matching, "_select_role", return_value="Content Marketeer") as sel, patch.object(
        matching.interimmer_repo, "get_by_role", return_value=[]
    ) as by_role, patch.object(matching, "_rank", return_value=MATCH) as rank:
        result = match(OPDRACHT, "transcript", limit=3)

    sel.assert_called_once()
    by_role.assert_called_once_with("Content Marketeer")
    rank.assert_called_once()
    assert result.shortlist[0].naam == "Niek Pijpers"


def test_create_match_returns_201_with_shortlist():
    analysis_id = _store_analysis()
    with patch("app.routers.matches.match", return_value=MATCH):
        response = client.post("/api/v1/matches", json={"analysis_id": analysis_id})

    assert response.status_code == 201
    body = response.json()
    assert body["analysis_id"] == analysis_id
    assert body["match_id"]
    assert body["shortlist"][0]["naam"] == "Niek Pijpers"
    assert body["aanbeveling"]


def test_create_match_unknown_analysis_returns_404():
    response = client.post("/api/v1/matches", json={"analysis_id": "nope"})
    assert response.status_code == 404


def test_create_match_provider_error_returns_502():
    analysis_id = _store_analysis()
    with patch("app.routers.matches.match", side_effect=MatchProviderError("boom")):
        response = client.post("/api/v1/matches", json={"analysis_id": analysis_id})
    assert response.status_code == 502
