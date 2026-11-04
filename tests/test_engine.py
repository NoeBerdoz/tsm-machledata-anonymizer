import pytest

from pii_anonymizer import engine
from pii_anonymizer.engine import CHUNK_SIZE, pseudonymize


@pytest.fixture
def model(monkeypatch):
    """Replace Ollama: the fake model finds the given pairs when they are in the text."""

    def install(*pairs):
        calls = []

        def ask_model(text):
            calls.append(text)
            return [pair for pair in pairs if pair[1] in text]

        monkeypatch.setattr(engine, "ask_model", ask_model)
        return calls

    install()
    return install


@pytest.mark.parametrize(
    ("value", "placeholder"),
    [
        ("756.1234.5678.97", "<AVS_1>"),
        ("7561234567897", "<AVS_1>"),
        ("CH93 0076 2011 6238 5295 7", "<IBAN_1>"),
        ("CH9300762011623852957", "<IBAN_1>"),
        ("marie.dupont@example.ch", "<EMAIL_1>"),
        ("+41 79 123 45 67", "<PHONE_1>"),
        ("0041 79 123 45 67", "<PHONE_1>"),
        ("+41 (0)79 123 45 67", "<PHONE_1>"),
        ("079 123 45 67", "<PHONE_1>"),
        ("+33 6 12 34 56 78", "<PHONE_1>"),
    ],
)
def test_regex_rules_mask_the_whole_value(model, value, placeholder):
    results, mapping = pseudonymize([f"Mon identifiant: {value}, merci."])
    assert results == [f"Mon identifiant: {placeholder}, merci."]
    assert mapping == {placeholder: value}


def test_text_without_personal_data_is_unchanged(model):
    text = "Trie la liste de 1200 éléments, version 3.13, le 12 mars."
    assert pseudonymize([text]) == ([text], {})


def test_same_value_gets_the_same_placeholder_in_every_text(model):
    model(("PERSON", "Marie Dupont"), ("PERSON", "Hans Müller"))
    results, mapping = pseudonymize(["Marie Dupont et Hans Müller", "Marie Dupont, encore"])
    assert results == ["<PERSON_1> et <PERSON_2>", "<PERSON_1>, encore"]
    assert mapping == {"<PERSON_1>": "Marie Dupont", "<PERSON_2>": "Hans Müller"}


def test_value_found_in_one_text_is_hidden_in_the_others(monkeypatch):
    monkeypatch.setattr(
        engine, "ask_model", lambda text: [("PERSON", "Dupont")] if "Madame" in text else []
    )
    results, _ = pseudonymize(["Madame Dupont", "DUPONT a appelé"])
    assert results == ["Madame <PERSON_1>", "<PERSON_2> a appelé"]


def test_value_broken_over_two_lines_is_found(model):
    model(("PERSON", "Marie Dupont"))
    results, mapping = pseudonymize(["Marie\nDupont et Marie Dupont"])
    assert results == ["<PERSON_1> et <PERSON_1>"]
    assert mapping == {"<PERSON_1>": "Marie Dupont"}


def test_overlapping_values_leave_nothing_visible(model):
    model(("ADDRESS", "Rue de Lausanne 12"), ("PERSON", "Lausanne 12, Fribourg"))
    results, _ = pseudonymize(["Rue de Lausanne 12, Fribourg."])
    assert results == ["<ADDRESS_1>."]


def test_regex_wins_over_the_model_on_the_same_value(model):
    model(("PERSON", "marie@example.ch"))
    assert pseudonymize(["marie@example.ch"])[0] == ["<EMAIL_1>"]


def test_invented_and_empty_values_are_ignored(monkeypatch):
    monkeypatch.setattr(
        engine, "ask_model", lambda _: [("PERSON", "Jean"), ("HEALTH", ""), ("PERSON", "a")]
    )
    text = "a b c"
    assert pseudonymize([text]) == ([text], {})


def test_value_is_not_matched_inside_a_word(model):
    model(("PERSON", "Ana"))
    assert pseudonymize(["Ana lit Banana"])[0] == ["<PERSON_1> lit Banana"]


def test_long_text_reaches_the_model_whole_and_in_chunks(model):
    calls = model(("PERSON", "Marie Dupont"))
    text = "x " * CHUNK_SIZE + "Marie Dupont"
    results, _ = pseudonymize([text])
    assert results[0].endswith("<PERSON_1>")
    assert len(calls) > 1
    assert max(map(len, calls)) <= CHUNK_SIZE


def test_value_on_a_chunk_edge_is_whole_in_one_chunk(model):
    calls = model()
    value = "Marie Dupont"
    pseudonymize(["x" * (CHUNK_SIZE - 5) + value])
    assert any(value in chunk for chunk in calls)


def test_ollama_failure_is_not_hidden(monkeypatch):
    def ask_model(_):
        raise OSError("connection refused")

    monkeypatch.setattr(engine, "ask_model", ask_model)
    with pytest.raises(OSError):
        pseudonymize(["marie@example.ch"])


def test_too_long_content_is_refused_before_ollama_can_cut_it():
    with pytest.raises(ValueError, match="too long"):
        engine.answer("x" * (engine.MAX_ANSWER_CHARS + 1))
