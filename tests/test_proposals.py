"""Tests for the proposal endpoint and email template."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import analyses as analysis_repo
from app.repositories import matches as match_repo
from app.schemas.analysis import IntakeExtractie, Opdracht
from app.schemas.matching import Candidate
from app.services.email_template import build_proposal_email
from app.services.proposal_intro import ProposalProviderError

client = TestClient(app)

OPDRACHT = Opdracht(
    functietitel="Content Marketeer",
    vereiste_skills=["Content marketing"],
    locatie="Rotterdam",
    startdatum="2026-05-18",
    einddatum="2026-10-10",
    tarief_min=70,
    tarief_max=80,
    urgentie="hoog",
)

CANDIDATES = [
    Candidate(
        naam="Henk van der Made", matchscore=83, matchuitleg="Sterke content-fit.",
        beschikbaarheid="32 uur, Hybride, max 60 minuten reistijd", uurtarief=85,
        specialisme="Content Marketeer", locatie="Noord-Brabant",
        competenties=["Content marketing", "Social media"],
    ),
    Candidate(
        naam="Gerrit van Oene", matchscore=80, matchuitleg="Content management ervaring.",
        beschikbaarheid="40 uur, Hybride, max 60 minuten reistijd", uurtarief=65,
        specialisme="Content Marketeer", locatie="Noord-Holland", competenties=["Content"],
    ),
]

INTRO = "<p>Hi Nadine,</p><p><strong>Behoefte</strong></p><ul><li><strong>Content:</strong> x</li></ul>"


def test_build_proposal_email_assembles_subject_and_body():
    subject, body = build_proposal_email(INTRO, CANDIDATES, "Nadine Jansen", "Profilians", OPDRACHT)
    assert subject == "Voorstel interim Content Marketeer — Profilians"
    assert INTRO in body  # LLM intro kept verbatim
    assert "1. Henk van der Made" in body
    assert "2. Gerrit van Oene" in body
    assert "€ 85,-" in body  # primary rate formatted
    assert "Gerrit" in body and "op projectbasis" in body  # secondary mentioned
    assert "Met vriendelijke groet," in body  # sign-off (name comes from the Gmail signature)


def _store_match() -> str:
    analysis = analysis_repo.save_analysis(
        transcript_id="t-1", opdracht_samenvatting=IntakeExtractie(opdracht=OPDRACHT)
    )
    match = match_repo.save_match(
        analysis_id=analysis.analysis_id, shortlist=CANDIDATES, aanbeveling="x"
    )
    return match.match_id


def test_create_proposal_returns_201():
    match_id = _store_match()
    with patch("app.routers.proposals.generate_intro", return_value=INTRO):
        response = client.post(
            "/api/v1/proposals",
            json={"match_id": match_id, "klant_naam": "Nadine Jansen", "klant_bedrijf": "Profilians"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["proposal_id"]
    assert body["subject"] == "Voorstel interim Content Marketeer — Profilians"
    assert "Henk van der Made" in body["body_html"]


def test_create_proposal_unknown_match_returns_404():
    response = client.post(
        "/api/v1/proposals",
        json={"match_id": "nope", "klant_naam": "X", "klant_bedrijf": "Y"},
    )
    assert response.status_code == 404


def test_create_proposal_provider_error_returns_502():
    match_id = _store_match()
    with patch("app.routers.proposals.generate_intro", side_effect=ProposalProviderError("boom")):
        response = client.post(
            "/api/v1/proposals",
            json={"match_id": match_id, "klant_naam": "Nadine", "klant_bedrijf": "Profilians"},
        )
    assert response.status_code == 502
