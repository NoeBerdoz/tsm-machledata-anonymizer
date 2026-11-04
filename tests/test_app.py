import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from pii_anonymizer import engine
from pii_anonymizer.feedback import FEEDBACK_FILE

APP = Path(engine.__file__).with_name("app.py")


@pytest.fixture(autouse=True)
def fake_model(monkeypatch, tmp_path):
    """Replace Ollama, record what it receives, and keep the feedback file out of the repo."""
    monkeypatch.chdir(tmp_path)
    received = []

    def answer(text):
        received.append(text)
        return "Bonjour <PERSON_1>"

    monkeypatch.setattr(engine, "ask_model", lambda _: [("PERSON", "Marie Dupont")])
    monkeypatch.setattr(engine, "answer", answer)
    return received


def run_with_prompt(prompt):
    page = AppTest.from_file(str(APP), default_timeout=30).run()
    page.text_area[0].set_value(prompt)
    return page.button[0].click().run()


def test_shows_pseudonymized_content_response_and_mapping():
    page = run_with_prompt("Marie Dupont, marie@example.ch")
    assert page.code[0].value == "<PERSON_1>, <EMAIL_1>"
    assert "Bonjour <PERSON_1>" in [element.value for element in page.markdown]
    assert any("Response time:" in element.value for element in page.caption)
    assert page.dataframe[0].value["Real value"].tolist() == ["Marie Dupont", "marie@example.ch"]


def test_the_model_only_receives_pseudonymized_content(fake_model):
    run_with_prompt("Marie Dupont, marie@example.ch")
    assert fake_model == ["<PERSON_1>, <EMAIL_1>"]


def test_rating_keeps_the_result_and_records_no_content():
    page = run_with_prompt("Marie Dupont")
    page = page.feedback[0].set_value(3).run()
    assert page.code[0].value == "<PERSON_1>"

    line = FEEDBACK_FILE.read_text(encoding="utf-8")
    assert json.loads(line)["stars"] == 4
    assert "PERSON" not in line
    assert "Marie" not in line


def test_removing_a_rating_records_nothing():
    page = run_with_prompt("Marie Dupont")
    page.feedback[0].set_value(None).run()
    assert not FEEDBACK_FILE.exists()


@pytest.mark.parametrize("failing", ["ask_model", "answer"])
def test_shows_nothing_when_the_model_fails(monkeypatch, failing):
    def fail(_):
        raise OSError("connection refused")

    monkeypatch.setattr(engine, failing, fail)
    page = run_with_prompt("marie@example.ch")
    assert "connection refused" in page.error[0].value
    assert not page.code


def test_a_failed_run_removes_the_previous_result(monkeypatch):
    page = run_with_prompt("Marie Dupont")

    def fail(_):
        raise OSError("connection refused")

    monkeypatch.setattr(engine, "answer", fail)
    page = page.button[0].click().run()
    assert page.error
    assert not page.code


def test_asks_for_input_when_empty():
    assert run_with_prompt("  ").warning
