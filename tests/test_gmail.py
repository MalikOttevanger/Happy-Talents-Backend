"""Tests for the Gmail signature + draft endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import proposals as proposal_repo
from app.services import gmail

client = TestClient(app)


def test_read_signature_returns_html():
    with patch("app.routers.gmail.gmail.get_signature", return_value="<p>Groet, Robert</p>"):
        response = client.get("/api/v1/users/me/signature")
    assert response.status_code == 200
    assert response.json()["signature_html"] == "<p>Groet, Robert</p>"


def test_read_signature_maps_gmail_error_to_502():
    with patch("app.routers.gmail.gmail.get_signature", side_effect=gmail.GmailError("nope")):
        response = client.get("/api/v1/users/me/signature")
    assert response.status_code == 502


def test_create_draft_appends_signature_and_returns_id():
    proposal = proposal_repo.save_proposal(subject="Voorstel", body_html="<p>Hi</p>")
    captured = {}

    def fake_create(to, subject, body_html):
        captured["body"] = body_html
        return "draft-123"

    with patch("app.routers.gmail.gmail.get_signature", return_value="<p>Robert</p>"), patch(
        "app.routers.gmail.gmail.create_draft", side_effect=fake_create
    ):
        response = client.post(
            "/api/v1/gmail/drafts",
            json={
                "proposal_id": proposal.proposal_id,
                "to": "klant@profilians.nl",
                "subject": "Voorstel",
                "body_html": "<p>Hi</p>",
            },
        )

    assert response.status_code == 201
    assert response.json()["gmail_draft_id"] == "draft-123"
    assert "<p>Robert</p>" in captured["body"]  # signature appended


def test_create_draft_unknown_proposal_returns_404():
    response = client.post(
        "/api/v1/gmail/drafts",
        json={"proposal_id": "nope", "to": "a@b.nl", "subject": "x", "body_html": "y"},
    )
    assert response.status_code == 404
