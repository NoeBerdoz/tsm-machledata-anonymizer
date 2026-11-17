import csv
import json
from hashlib import file_digest
from shutil import copytree

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("gliner2")

from gliner2 import AutoExtractor, ExtractorConfig  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402
from tokenizers.models import WordLevel  # noqa: E402
from tokenizers.pre_tokenizers import Whitespace  # noqa: E402
from transformers import DebertaV2Config, PreTrainedTokenizerFast  # noqa: E402

from pii_anonymizer.evaluate import DETECTORS, evaluate  # noqa: E402
from pii_anonymizer.quantize_gliner2 import (  # noqa: E402
    MANIFEST_FILE,
    WEIGHTS_FILE,
    load_int8_model,
    main,
)


def tiny_model(architecture, **options):
    words = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "Alice", "writes"]
    tokenizer = Tokenizer(WordLevel({word: index for index, word in enumerate(words)}, "[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=tokenizer,
        pad_token="[PAD]",
        unk_token="[UNK]",
        cls_token="[CLS]",
        sep_token="[SEP]",
        mask_token="[MASK]",
    )
    encoder = DebertaV2Config(
        vocab_size=len(words),
        hidden_size=8,
        intermediate_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        relative_attention=True,
    )
    config = ExtractorConfig(model_name="local-encoder", architecture=architecture, **options)
    return AutoExtractor.from_config(config, encoder_config=encoder, tokenizer=tokenizer).eval()


@pytest.mark.parametrize("architecture", ["span", "boundary"])
def test_gliner2_int8_folder_loads_without_original_weights(tmp_path, monkeypatch, architecture):
    source = tmp_path / "fp32"
    destination = tmp_path / "int8"
    model = tiny_model(architecture)
    model.save_pretrained(source)
    main([str(source), str(destination)])
    (source / "model.safetensors").unlink()
    emitted = {p for p in destination.rglob("*") if p.is_file()}
    manifest = json.loads((destination / MANIFEST_FILE).read_text())
    assert manifest["source_model"] == source.name
    assert {destination / name for name in manifest["files"]} == emitted
    with (destination / WEIGHTS_FILE).open("rb") as weights:
        digest = file_digest(weights, "sha256").hexdigest()
    assert manifest["weights_sha256"] == digest
    assert [p.name for p in destination.rglob("*") if p.is_file() and p.suffix != ".json"] == [
        WEIGHTS_FILE
    ]

    model = load_int8_model(destination)
    assert model.architecture == architecture
    assert model.encoder.get_input_embeddings().weight().dtype == torch.quint8
    if architecture == "span":
        with torch.inference_mode():
            logits = model._compute_span_scores_core(
                torch.ones(1, 2, 8), torch.ones(1, 1, 8), torch.tensor([2])
            )
        assert torch.isfinite(logits[0, 0, 0, :2]).all()
        assert torch.isneginf(logits[0, 0, 1, 1])

    monkeypatch.setenv("GLINER2_INT8_DIR", str(destination))
    (destination / "build.log").write_text("local notes")
    detector = DETECTORS["gliner2-int8"]()
    assert set(detector.files) == emitted
    assert f"source={source.name} sha256:{manifest['artifact_sha256']}" in detector.runtime
    assert all(
        0 <= span.start < span.end <= len("Alice writes")
        for span in detector.detect("Alice writes")
    )


def test_int8_tokenizer_variants_keep_separate_evaluation_rows(tmp_path, monkeypatch):
    first_source = tmp_path / "original" / "checkpoint"
    second_source = tmp_path / "swapped" / "checkpoint"
    tiny_model("span").save_pretrained(first_source)
    copytree(first_source, second_source)
    tokenizer_path = second_source / "tokenizer.json"
    tokenizer = json.loads(tokenizer_path.read_text())
    vocab = tokenizer["model"]["vocab"]
    vocab["Alice"], vocab["writes"] = vocab["writes"], vocab["Alice"]
    tokenizer_path.write_text(json.dumps(tokenizer))

    first = tmp_path / "original-int8"
    second = tmp_path / "swapped-int8"
    main([str(first_source), str(first)])
    main([str(second_source), str(second)])
    manifest = json.loads((first / MANIFEST_FILE).read_text())
    second_manifest = json.loads((second / MANIFEST_FILE).read_text())
    assert manifest["source_model"] == second_manifest["source_model"]
    assert manifest["files"] == second_manifest["files"]
    changed = {
        name
        for name in manifest["files"]
        if name != MANIFEST_FILE and (first / name).read_bytes() != (second / name).read_bytes()
    }
    assert changed == {"tokenizer.json"}

    dataset = tmp_path / "t1.jsonl"
    dataset.write_text(
        '{"id":"1","text":"Alice writes","entities":[{"start":0,"end":5,"label":"PERSON"}]}\n'
    )
    out = tmp_path / "results"
    monkeypatch.setattr("pii_anonymizer.evaluate.cpu_name", lambda: "Test CPU")
    for folder in (first, second):
        monkeypatch.setenv("GLINER2_INT8_DIR", str(folder))
        evaluate("gliner2-int8", DETECTORS["gliner2-int8"](), dataset, out)

    for name in ("results.csv", "recall_per_type.csv"):
        with (out / name).open(newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert len({row["runtime"] for row in rows}) == 2


def test_int8_count_lstm_v2_extracts_entities(tmp_path):
    model = tiny_model("span", counting_layer="count_lstm_v2", max_width=1)
    with torch.no_grad():
        count = model.count_pred[-1]
        count.weight.zero_()
        count.bias.zero_()
        count.bias[1] = 10
        # Make the span and its query agree regardless of the random encoder weights.
        for projection in (
            model.count_embed.transformer.out_projector[-1],
            model.span_rep.span_rep_layer.out_project[-1],
        ):
            projection.weight.zero_()
            projection.bias.fill_(1)

    text = "Alice writes"
    expected = model.extract_entities(text, ["person"], include_spans=True)
    assert expected["entities"]["person"]
    source = tmp_path / "fp32"
    destination = tmp_path / "int8"
    model.save_pretrained(source)
    main([str(source), str(destination)])
    reloaded = load_int8_model(destination)
    layer = reloaded.count_embed.transformer.transformer.layers[0]
    assert layer.linear1.weight().dtype == torch.qint8
    assert reloaded.extract_entities(text, ["person"], include_spans=True) == expected
