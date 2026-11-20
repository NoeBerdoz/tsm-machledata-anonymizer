import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from pii_anonymizer import backend, client, engine

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    """Replace the LLM and record what it receives."""
    monkeypatch.setenv("PII_BACKEND_TOKEN", TOKEN)
    received = []

    def answer(text):
        received.append(text)
        return "Bonjour <PERSON_1>, votre IBAN <IBAN_1> est noté."

    monkeypatch.setattr(engine, "answer", answer)
    return received


@pytest.fixture
def api():
    return TestClient(backend.app)


def test_returns_the_response_with_its_placeholders_unchanged(api, fake_llm):
    reply = api.post("/answer", json={"text": "<PERSON_1>, <IBAN_1>"}, headers=AUTH)
    assert reply.status_code == 200
    assert reply.json() == {"response": "Bonjour <PERSON_1>, votre IBAN <IBAN_1> est noté."}
    assert fake_llm == ["<PERSON_1>, <IBAN_1>"]


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": TOKEN}]
)
def test_refuses_a_request_without_the_right_token(api, fake_llm, headers):
    assert api.post("/answer", json={"text": "x"}, headers=headers).status_code == 401
    assert fake_llm == []


def test_refuses_everything_when_no_token_is_configured(api, fake_llm, monkeypatch):
    monkeypatch.delenv("PII_BACKEND_TOKEN")
    assert (
        api.post("/answer", json={"text": "x"}, headers={"Authorization": "Bearer "}).status_code
        == 401
    )
    assert fake_llm == []


@pytest.mark.parametrize(
    ("error", "status"), [(ValueError("too long (9 of 8 characters)"), 413), (OSError("down"), 502)]
)
def test_llm_errors_become_http_errors(api, monkeypatch, error, status):
    def fail(_):
        raise error

    monkeypatch.setattr(engine, "answer", fail)
    assert api.post("/answer", json={"text": "x"}, headers=AUTH).status_code == status


def test_logs_hold_no_content(api, monkeypatch, caplog):
    secret = "<PERSON_1> lives at Rue Secrète 12"

    def fail(_):
        raise OSError("down")

    with caplog.at_level(logging.DEBUG):
        api.post("/answer", json={"text": secret}, headers=AUTH)
        monkeypatch.setattr(engine, "answer", fail)
        reply = api.post("/answer", json={"text": secret}, headers=AUTH)
    assert "Secrète" not in caplog.text
    assert "Secrète" not in reply.text


def test_client_sends_the_text_with_the_token(monkeypatch):
    sent = {}

    def urlopen(request, timeout):
        sent["url"], sent["body"] = request.full_url, json.loads(request.data)
        sent["auth"] = request.get_header("Authorization")
        return io.BytesIO(b'{"response": "Bonjour <PERSON_1>"}')

    monkeypatch.setattr(client.urllib.request, "urlopen", urlopen)
    assert client.ask_backend("<PERSON_1>") == "Bonjour <PERSON_1>"
    assert sent == {
        "url": f"{client.BACKEND_URL}/answer",
        "body": {"text": "<PERSON_1>"},
        "auth": f"Bearer {TOKEN}",
    }
