import pytest

from pii_anonymizer import engine
from pii_anonymizer.engine import CHUNK_SIZE, detect, pseudonymize, restore
from pii_anonymizer.spans import Span


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
        ("079/123 45 67", "<PHONE_1>"),
        ("0041791234567", "<PHONE_1>"),
        ("756-1234-5678-97", "<AVS_1>"),
        ("ch93 0076 2011 6238 5295 7", "<IBAN_1>"),
    ],
)
def test_regex_rules_mask_the_whole_value(model, value, placeholder):
    results, mapping, _ = pseudonymize([f"Mon identifiant: {value}, merci."])
    assert results == [f"Mon identifiant: {placeholder}, merci."]
    assert mapping == {placeholder: value}


@pytest.mark.parametrize(
    "text",
    [
        "Trie la liste de 1200 éléments, version 3.13, le 12 mars.",
        "build 0012345678 failed",
        "order 00123456789 shipped",
        "request 4f1c2d3e-0000-1111-2222-333344445555 timed out",
        "request 9b2e0041-7912-3456-7890-abcdef012345 timed out",
        "product code AB12CDEF34GH",
    ],
)
def test_text_without_personal_data_is_unchanged(model, text):
    assert pseudonymize([text]) == ([text], {}, [])


def test_same_value_gets_the_same_placeholder_in_every_text(model):
    model(("PERSON", "Marie Dupont"), ("PERSON", "Hans Müller"))
    results, mapping, _ = pseudonymize(["Marie Dupont et Hans Müller", "Marie Dupont, encore"])
    assert results == ["<PERSON_1> et <PERSON_2>", "<PERSON_1>, encore"]
    assert mapping == {"<PERSON_1>": "Marie Dupont", "<PERSON_2>": "Hans Müller"}


def test_value_found_in_one_text_is_hidden_in_the_others(monkeypatch):
    monkeypatch.setattr(
        engine, "ask_model", lambda text: [("PERSON", "Dupont")] if "Madame" in text else []
    )
    results, _, missed = pseudonymize(["Madame Dupont", "DUPONT a appelé"])
    assert results == ["Madame <PERSON_1>", "<PERSON_2> a appelé"]
    assert missed == []


def test_value_broken_over_two_lines_is_found(model):
    model(("PERSON", "Marie Dupont"))
    results, mapping, _ = pseudonymize(["Marie\nDupont et Marie Dupont"])
    assert results == ["<PERSON_1> et <PERSON_1>"]
    assert mapping == {"<PERSON_1>": "Marie Dupont"}


def test_overlapping_values_leave_nothing_visible(model):
    model(("ADDRESS", "Rue de Lausanne 12"), ("PERSON", "Lausanne 12, Fribourg"))
    results, _, _ = pseudonymize(["Rue de Lausanne 12, Fribourg."])
    assert results == ["<ADDRESS_1>."]


def test_regex_wins_over_the_model_on_the_same_value(model):
    model(("PERSON", "marie@example.ch"))
    assert pseudonymize(["marie@example.ch"])[0] == ["<EMAIL_1>"]


def test_empty_values_are_ignored(monkeypatch):
    monkeypatch.setattr(
        engine, "ask_model", lambda _: [("HEALTH", ""), ("PERSON", "a"), ("PERSON", "--")]
    )
    text = "a b -- c"
    assert pseudonymize([text]) == ([text], {}, [])


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("Favre Claire, née le 3.7.1990", "Claire Favre"),
        ("Favre Claire, née le 3.7.1990", "03/07/1990"),
        ("Chemin des Lilas 4, 1950 Sion", "Chemin des Lilas 4 à Sion"),
        ("a b c", "Jean"),
    ],
)
def test_values_not_found_in_the_text_are_reported(monkeypatch, text, value):
    """Invented or written differently from the text: the code cannot tell, so it reports both."""
    monkeypatch.setattr(engine, "ask_model", lambda _: [("PERSON", value)])
    assert pseudonymize([text]) == ([text], {}, [value])


def test_hyphen_and_space_are_interchangeable_in_a_name(monkeypatch):
    monkeypatch.setattr(engine, "ask_model", lambda _: [("PERSON", "Jean Luc Rochat")])
    assert pseudonymize(["Jean-Luc Rochat"]) == (
        ["<PERSON_1>"],
        {"<PERSON_1>": "Jean-Luc Rochat"},
        [],
    )


def test_value_cut_by_a_chunk_edge_is_not_reported(monkeypatch):
    monkeypatch.setattr(
        engine, "ask_model", lambda _: [("PERSON", "Marie Dup"), ("PERSON", "Marie Dupont")]
    )
    assert pseudonymize(["Marie Dupont"])[2] == []


def test_value_is_not_matched_inside_a_word(model):
    model(("PERSON", "Ana"))
    assert pseudonymize(["Ana lit Banana"])[0] == ["<PERSON_1> lit Banana"]


def test_long_text_reaches_the_model_whole_and_in_chunks(model):
    calls = model(("PERSON", "Marie Dupont"))
    text = "x " * CHUNK_SIZE + "Marie Dupont"
    results, _, _ = pseudonymize([text])
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


def test_placeholder_already_in_the_input_is_never_given_to_a_value(model):
    model(("PERSON", "Marie Dupont"))
    text = "Marie Dupont a lu la note sur <PERSON_1> et person_2."
    results, mapping, _ = pseudonymize([text])
    assert results == ["<PERSON_3> a lu la note sur <PERSON_1> et person_2."]
    assert mapping == {"<PERSON_3>": "Marie Dupont"}


def test_detect_returns_the_spans_of_the_model_and_the_rules(model):
    model(("PERSON", "Marie Dupont"))
    text = "Marie Dupont, marie@example.ch, 079 123 45 67"
    spans = detect(text)
    assert spans == [Span(0, 12, "PERSON"), Span(14, 30, "EMAIL"), Span(32, 45, "PHONE")]
    assert [text[s.start : s.end] for s in spans] == [
        "Marie Dupont",
        "marie@example.ch",
        "079 123 45 67",
    ]


def test_detect_merges_overlapping_values_into_one_span(model):
    model(("PERSON", "Marie Dupont"), ("ADDRESS", "Dupont marie"))
    assert detect("Marie Dupont marie@example.ch") == [Span(0, 29, "PERSON")]


# Outputs of pseudonymize() recorded before detect() was split from it: they must not change.
LONG = "x " * CHUNK_SIZE + "Marie Dupont prend de l'insuline. " + "y " * CHUNK_SIZE
FIXED_CASES = [
    (
        [("PERSON", "Marie Dupont"), ("PERSON", "Hans Müller")],
        [
            "Marie Dupont a écrit à Hans Müller, puis Marie Dupont a rappelé.",
            "MARIE DUPONT et Hans Müller, encore Hans Müller.",
        ],
        (
            [
                "<PERSON_1> a écrit à <PERSON_2>, puis <PERSON_1> a rappelé.",
                "<PERSON_3> et <PERSON_2>, encore <PERSON_2>.",
            ],
            {
                "<PERSON_1>": "Marie Dupont",
                "<PERSON_2>": "Hans Müller",
                "<PERSON_3>": "MARIE DUPONT",
            },
            [],
        ),
    ),
    (
        [("PERSON", "Marie Dupont"), ("ADDRESS", "Dupont marie")],
        ["Contact: Marie Dupont marie@example.ch, 079 123 45 67 Marie Dupont."],
        (
            ["Contact: <PERSON_1>, <PHONE_1> <PERSON_2>."],
            {
                "<PERSON_1>": "Marie Dupont marie@example.ch",
                "<PHONE_1>": "079 123 45 67",
                "<PERSON_2>": "Marie Dupont",
            },
            [],
        ),
    ),
    (
        [("PERSON", "Marie Dupont"), ("HEALTH", "insuline")],
        [LONG + "Marie Dupont, +41 79 123 45 67."],
        (
            [
                "x " * CHUNK_SIZE
                + "<PERSON_1> prend de l'<HEALTH_1>. "
                + "y " * CHUNK_SIZE
                + "<PERSON_1>, <PHONE_1>."
            ],
            {
                "<PERSON_1>": "Marie Dupont",
                "<HEALTH_1>": "insuline",
                "<PHONE_1>": "+41 79 123 45 67",
            },
            [],
        ),
    ),
]


@pytest.mark.parametrize(("pairs", "texts", "expected"), FIXED_CASES)
def test_pseudonymize_output_is_unchanged_on_fixed_examples(model, pairs, texts, expected):
    model(*pairs)
    assert pseudonymize(texts) == expected


def test_pseudonymize_output_is_unchanged_when_a_value_is_not_in_the_text(monkeypatch):
    monkeypatch.setattr(
        engine, "ask_model", lambda _: [("PERSON", "Claire Favre"), ("DATE_OF_BIRTH", "3.7.1990")]
    )
    assert pseudonymize(["Favre Claire, née le 3.7.1990, IBAN CH93 0076 2011 6238 5295 7."]) == (
        ["Favre Claire, née le <DATE_OF_BIRTH_1>, IBAN <IBAN_1>."],
        {"<DATE_OF_BIRTH_1>": "3.7.1990", "<IBAN_1>": "CH93 0076 2011 6238 5295 7"},
        ["Claire Favre"],
    )


MAPPING = {"<PERSON_1>": "Marie Dupont", "<PERSON_2>": "Hans Müller", "<EMAIL_1>": "m@example.ch"}


def test_every_placeholder_comes_back_to_exactly_its_value():
    response, unknown = restore("<PERSON_1>, <PERSON_2>: <EMAIL_1>. <PERSON_1>!", MAPPING, [])
    assert response == "Marie Dupont, Hans Müller: m@example.ch. Marie Dupont!"
    assert unknown == []


@pytest.mark.parametrize(
    "token", ["<PERSON_3>", "PERSON_1", "<person_1>", "<PERSON_1", "[PERSON_2]"]
)
def test_unknown_or_changed_placeholder_is_shown_as_it_is_and_reported(token):
    response, unknown = restore(f"Bonjour {token}.", MAPPING, [])
    assert response == f"Bonjour {token}."
    assert unknown == [token.strip("[]")]


def test_placeholder_written_by_the_user_is_kept_without_warning():
    """The input already had <PERSON_1>, so pseudonymize gave the real name <PERSON_2>."""
    sent = ["<PERSON_2> a lu la note sur <PERSON_1>."]
    response, unknown = restore("<PERSON_2> parle de <PERSON_1>.", {"<PERSON_2>": "Marie"}, sent)
    assert response == "Marie parle de <PERSON_1>."
    assert unknown == []


def test_value_that_looks_like_a_placeholder_is_not_replaced_in_turn():
    response, _ = restore("<PERSON_1>", {"<PERSON_1>": "<PERSON_2>", "<PERSON_2>": "Hans"}, [])
    assert response == "<PERSON_2>"


def test_pseudonymize_then_restore_gives_back_the_real_values(model):
    model(("PERSON", "Marie Dupont"))
    texts, mapping, _ = pseudonymize(["Marie Dupont, marie@example.ch, 079 123 45 67"])
    assert restore(texts[0], mapping, texts) == (
        "Marie Dupont, marie@example.ch, 079 123 45 67",
        [],
    )
