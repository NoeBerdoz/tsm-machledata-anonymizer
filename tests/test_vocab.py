from types import SimpleNamespace

from pii_anonymizer.vocab import token_counts


class FakeTokenizer:
    """Splits on spaces and gives each word a fixed ID."""

    ids = {"Marie": 1, "Dupont": 2, "habite": 3, "Sion": 4}

    def encode_batch(self, texts, add_special_tokens):
        assert add_special_tokens is False
        return [SimpleNamespace(ids=[self.ids[w] for w in text.split()]) for text in texts]


def test_token_counts_add_up_across_batches():
    texts = ["Marie Dupont", "Marie habite Sion", "Dupont"]
    assert token_counts(texts, FakeTokenizer(), batch=2) == {1: 2, 2: 2, 3: 1, 4: 1}
