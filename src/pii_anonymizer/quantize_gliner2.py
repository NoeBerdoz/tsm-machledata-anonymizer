"""Write or load a CPU int8 GLiNER2 checkpoint."""

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import torch
from gliner2 import AutoExtractor, ExtractorConfig, SpanExtractor
from gliner2.configuration import architecture_from_config
from gliner2.models.base import load_extractor_tokenizer
from torch import nn
from transformers import AutoConfig

from pii_anonymizer.quantization import load_quantized_weights, quantize_weights

WEIGHTS_FILE = "model-int8.pt"
MANIFEST_FILE = "quantization.json"
FLOAT_ACTIVATION_PATTERN = re.compile(r"encoder\.encoder\.layer\.\d+\.output\.dense")
# Files from converters that predate the manifest, including optional tokenizer assets.
LEGACY_FILES = (
    WEIGHTS_FILE,
    "config.json",
    "encoder_config/config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "tokenizer.model",
    "added_tokens.json",
    "special_tokens_map.json",
    "merges.txt",
    "vocab.json",
    "vocab.txt",
    "spiece.model",
    "sentencepiece.bpe.model",
)


@dataclass(frozen=True)
class Int8Artifact:
    source_model: str
    artifact_sha256: str
    files: tuple[Path, ...]


class Int8SpanExtractor(SpanExtractor):
    def _compute_span_scores_core(self, padded, queries, text_len_t, mask_invalid=True):
        # The factorized scorer reads two linear weight matrices directly. Use the
        # existing span forward pass so those layers run their dynamic int8 kernels.
        spans, _, invalid = self._compute_span_rep_core(padded, text_len_t)
        logits = torch.einsum("blwh,bqh->bqlw", spans, queries)
        if mask_invalid:
            invalid = invalid.reshape(spans.shape[:3])
            logits = logits.masked_fill(invalid[:, None], -torch.inf)
        return logits


def _source_model(source: Path) -> str:
    source = source.resolve()
    cache_name = source.parent.parent.name
    if source.parent.name == "snapshots" and cache_name.startswith("models--"):
        model = cache_name.removeprefix("models--").replace("--", "/")
        return f"{model}@{source.name}"
    return source.name


def _inference_file_digests(folder: Path, files: Sequence[Path]) -> dict[str, bytes]:
    digests = {}
    for path in files:
        name = path.relative_to(folder).as_posix()
        if name != MANIFEST_FILE:
            with path.open("rb") as file:
                digests[name] = file_digest(file, "sha256").digest()
    return digests


def _artifact_sha256(digests: dict[str, bytes]) -> str:
    digest = sha256()
    # Include relative names in a stable order so swapping two files changes the digest.
    for name, file_sha256 in sorted(digests.items()):
        digest.update(name.encode("utf-8") + b"\0" + file_sha256)
    return digest.hexdigest()


def read_int8_artifact(folder: Path) -> Int8Artifact:
    """Read the converter's provenance and emitted files for evaluation."""
    manifest = folder / MANIFEST_FILE
    if not manifest.is_file():
        files = tuple(folder / name for name in LEGACY_FILES if (folder / name).is_file())
        return Int8Artifact(
            "legacy", _artifact_sha256(_inference_file_digests(folder, files)), files
        )

    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    files = tuple(folder / name for name in metadata["files"])
    root = folder.resolve()
    if any(not path.resolve().is_relative_to(root) for path in files):
        raise ValueError(f"File outside the model folder in {manifest}")
    digests = _inference_file_digests(folder, files)
    digest = _artifact_sha256(digests)
    if metadata.get("artifact_sha256", digest) != digest:
        raise ValueError(f"Artifact digest does not match {manifest}")
    if metadata["weights_sha256"] != digests[WEIGHTS_FILE].hex():
        raise ValueError(f"Weight digest does not match {manifest}")
    return Int8Artifact(metadata["source_model"], digest, files)


def write_int8_model(source: Path, destination: Path) -> None:
    """Convert a local GLiNER2 model folder and publish it at a new path."""
    if not source.is_dir():
        raise NotADirectoryError(source)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)

    model = AutoExtractor.from_pretrained(
        str(source), map_location="cpu", attention_backend="standard"
    )
    quantize_weights(model, model.encoder.get_input_embeddings())
    model.config.architecture = model.architecture

    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as temp:
        folder = Path(temp) / "model"
        folder.mkdir()
        model.config.save_pretrained(folder)
        model.encoder.config.save_pretrained(folder / "encoder_config")
        model.processor.tokenizer.save_pretrained(folder)
        torch.save(model.state_dict(), folder / WEIGHTS_FILE)
        files = [path for path in folder.rglob("*") if path.is_file()]
        digests = _inference_file_digests(folder, files)
        manifest = {
            "source_model": _source_model(source),
            "weights_sha256": digests[WEIGHTS_FILE].hex(),
            "artifact_sha256": _artifact_sha256(digests),
            "files": sorted([*digests, MANIFEST_FILE]),
        }
        (folder / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        folder.rename(destination)


def load_int8_model(folder: Path) -> nn.Module:
    """Construct a GLiNER2 model from local configs and load only its int8 checkpoint."""
    weights = folder / WEIGHTS_FILE
    if not weights.is_file():
        raise FileNotFoundError(weights)
    config = ExtractorConfig.from_pretrained(str(folder), local_files_only=True)
    encoder_config = AutoConfig.from_pretrained(
        str(folder / "encoder_config"), local_files_only=True
    )
    tokenizer = load_extractor_tokenizer(str(folder))
    options = {"encoder_config": encoder_config, "tokenizer": tokenizer, "use_flashdeberta": False}
    if architecture_from_config(config) == "span":
        model = Int8SpanExtractor(config, **options)
    else:
        model = AutoExtractor.from_config(config, **options)
    model.quantization_runtime = load_quantized_weights(
        model,
        model.encoder.get_input_embeddings(),
        weights,
        float_activation_pattern=FLOAT_ACTIVATION_PATTERN,
    )
    model.encoder.config.vocab_size = model.encoder.get_input_embeddings().num_embeddings
    return model


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("in_folder", type=Path)
    parser.add_argument("out_folder", type=Path)
    args = parser.parse_args(argv)
    write_int8_model(args.in_folder, args.out_folder)


if __name__ == "__main__":
    main()
