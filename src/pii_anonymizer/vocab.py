"""How much of the teacher's vocabulary our four languages use.

Usage:
    uv run --group baselines python -m pii_anonymizer.vocab

GLiNER2-PII keeps 768 numbers for each of its 250,112 tokens, and these word embeddings are
63 % of its parameters. Most tokens belong to languages we do not need. This counts the
distinct tokens that its tokenizer gives the French, German, Italian and English texts of
the OpenPII-1M validation split (pinned commit), plus the special tokens, and prints what a
vocabulary pruned to them would weigh in int8. It is a lower bound for a real pruning,
which counts the training texts too. It also prints how many tokens remain if the rare ones
are dropped, and which share of the text they still cover. See docs/baselines.md.
"""

from collections import Counter
from collections.abc import Iterable

from pii_anonymizer.baselines import GLINER2_MODEL, GLINER2_REVISION, disable_hf_telemetry
from pii_anonymizer.public_data import LANGUAGES, SOURCES, load_validation

EMBEDDING_DIM = 768
BATCH = 1000
MIN_COUNTS = (2, 5, 10)


def token_counts(texts: Iterable[str], tokenizer, batch: int = BATCH) -> Counter:
    """How many times each token ID occurs in the texts, special tokens excluded."""
    counts: Counter = Counter()
    texts = list(texts)
    for start in range(0, len(texts), batch):
        for encoding in tokenizer.encode_batch(
            texts[start : start + batch], add_special_tokens=False
        ):
            counts.update(encoding.ids)
    return counts


def main() -> None:
    disable_hf_telemetry()
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    path = hf_hub_download(GLINER2_MODEL, "tokenizer.json", revision=GLINER2_REVISION)
    tokenizer = Tokenizer.from_file(path)
    special = set(tokenizer.get_added_tokens_decoder())
    rows = load_validation(SOURCES["t1-openpii-1m"])

    total = tokenizer.get_vocab_size()
    counts: Counter = Counter()
    for lang in LANGUAGES:
        texts = [row["source_text"] for row in rows if row["language"] == lang]
        per_lang = token_counts(texts, tokenizer)
        counts.update(per_lang)
        print(f"{lang}: {len(texts):,} texts, {len(per_lang):,} distinct tokens")

    kept = len(set(counts) | special)
    print(f"all four: {kept:,} of {total:,} tokens ({kept / total:.1%}), special tokens included")
    print(
        f"embeddings: {total * EMBEDDING_DIM / 1e6:.1f}M parameters now, "
        f"{kept * EMBEDDING_DIM / 1e6:.1f}M after pruning, "
        f"about {kept * EMBEDDING_DIM / 1e6:.0f} MB in int8"
    )
    occurrences = sum(counts.values())
    for min_count in MIN_COUNTS:
        frequent = [token for token, n in counts.items() if n >= min_count]
        share = sum(counts[token] for token in frequent) / occurrences
        print(
            f"seen at least {min_count} times: {len(frequent):,} tokens, "
            f"{len(frequent) * EMBEDDING_DIM / 1e6:.1f}M parameters, {share:.2%} of the text"
        )


if __name__ == "__main__":
    main()
