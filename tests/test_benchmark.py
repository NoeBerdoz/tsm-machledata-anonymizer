import pytest

import pii_anonymizer.benchmark
from pii_anonymizer.benchmark import cpu_name, measure_latency, percentile, size_on_disk


def test_size_of_a_folder_and_a_file(tmp_path):
    model = tmp_path / "model"
    (model / "tokenizer").mkdir(parents=True)
    (model / "weights.bin").write_bytes(b"x" * 1000)
    (model / "tokenizer" / "vocab.txt").write_bytes(b"x" * 200)
    config = tmp_path / "config.json"
    config.write_bytes(b"x" * 30)
    assert size_on_disk([model, config]) == 1230
    # A file listed twice is counted once.
    assert size_on_disk([model, model / "weights.bin"]) == 1200


def test_size_of_a_missing_file_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        size_on_disk([tmp_path / "missing.bin"])


def test_percentile_interpolates():
    values = [float(v) for v in range(1, 11)]
    assert percentile(values, 50) == pytest.approx(5.5)
    assert percentile(values, 95) == pytest.approx(9.55)


class FakeClock:
    """A clock that only moves when the fake detector runs."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_latency_percentiles_from_a_fake_detector():
    clock = FakeClock()
    calls = []

    def detect(text):
        calls.append(text)
        # One millisecond per word.
        clock.now += len(text.split()) / 1000
        return []

    texts = ["one two", "one two three four"]
    latency = measure_latency(detect, texts, warmup=3, runs=5, clock=clock)

    assert len(calls) == 3 + 2 * 5
    assert latency.calls == 10
    # Five calls at 2 ms and five at 4 ms.
    assert latency.p50_ms == pytest.approx(3.0)
    assert latency.p95_ms == pytest.approx(4.0)
    # Every call costs 1 ms per word, so 100 ms per 100 words.
    assert latency.p50_ms_per_100_words == pytest.approx(100.0)
    assert latency.p95_ms_per_100_words == pytest.approx(100.0)


def test_latency_needs_texts():
    with pytest.raises(ValueError):
        measure_latency(lambda text: [], [])


def test_cpu_name_is_a_non_empty_string():
    name = cpu_name()
    assert isinstance(name, str)
    assert name


def test_cpu_name_never_raises(monkeypatch):
    def broken():
        raise OSError("no access")

    monkeypatch.setattr(pii_anonymizer.benchmark, "_read_cpu_name", broken)
    monkeypatch.setattr(pii_anonymizer.benchmark.platform, "processor", lambda: "")
    assert cpu_name() == "unknown"

    monkeypatch.setattr(pii_anonymizer.benchmark.platform, "processor", lambda: "x86_64")
    assert cpu_name() == "x86_64"
