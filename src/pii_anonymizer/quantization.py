"""PyTorch CPU quantization for linear layers and a word embedding."""

import platform
import re
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from threading import Lock

import torch
from torch import nn
from torch.ao.nn.quantized import Embedding as QuantizedEmbedding
from torch.ao.nn.quantized.dynamic import Linear as QuantizedLinear
from torch.ao.quantization import (
    default_dynamic_qconfig,
    float_qparams_weight_only_qconfig,
    quantize_dynamic,
)


@dataclass(frozen=True)
class QuantizationRuntime:
    engine: str
    activation_range: str
    float_activation_layers: int


class _ActivationRangeLinear(QuantizedLinear):
    reduce_range = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.ops.quantized.linear_dynamic(
            x, self._packed_params._packed_params, reduce_range=self.reduce_range
        ).to(x.dtype)


_ENGINE_LOCK = Lock()


def _engine_preferences(machine: str, supported: Sequence[str]) -> tuple[str, ...]:
    machine = machine.lower()
    if machine in ("x86_64", "amd64", "x86", "i386", "i686"):
        engines = ("onednn", "x86", "fbgemm", "qnnpack")
    elif machine.startswith(("arm", "aarch64")):
        engines = ("qnnpack", "onednn", "x86", "fbgemm")
    else:
        engines = ("x86", "fbgemm", "qnnpack", "onednn")
    choices = tuple(engine for engine in engines if engine in supported)
    if not choices:
        raise RuntimeError(f"No supported PyTorch CPU quantization engine in {supported}")
    return choices


@contextmanager
def _preserve_engine():
    with _ENGINE_LOCK:
        backend = torch.backends.quantized
        previous = backend.engine
        try:
            yield backend
        finally:
            # Some builds start with an unset engine that their setter cannot restore.
            if previous in backend.supported_engines and backend.engine != previous:
                backend.engine = previous


@cache
def _supports_full_range(engine: str) -> bool:
    # Packing uses the active engine. Cache the check for each engine used in this process.
    # Multiplying 255 by 127 twice overflows a signed 16-bit sum.
    inputs = torch.ones(1, 2, dtype=torch.float32)
    weights = torch.quantize_per_tensor(inputs, 1 / 127, 0, torch.qint8)
    packed = torch.ops.quantized.linear_prepack(weights, None)
    result = torch.ops.quantized.linear_dynamic(inputs, packed, reduce_range=False)
    return abs(result.item() - 2.0) < 0.01


def _select_load_engine(engines: Sequence[str], mixed: bool) -> tuple[str, bool]:
    backend = torch.backends.quantized
    failures = []
    first_error = None
    for engine in engines:
        try:
            backend.engine = engine
            full_range = (mixed or engine == "qnnpack" or bool(failures)) and _supports_full_range(
                engine
            )
        except RuntimeError as error:
            if first_error is None:
                first_error = error
            failures.append(
                f"{engine.upper() if engine == 'qnnpack' else engine} failed the probe."
            )
            continue
        # QNNPACK ignores reduce_range, so it must pass the check to remain usable.
        if engine == "qnnpack" and not full_range:
            failures.append("QNNPACK failed the full-range activation check.")
            continue
        return engine, full_range
    message = " ".join(["No usable PyTorch quantization engine.", *failures])
    raise RuntimeError(message) from first_error


def _float_linear(module: QuantizedLinear) -> nn.Linear:
    weight = module.weight().dequantize()
    bias = module.bias()
    linear = nn.Linear(module.in_features, module.out_features, bias is not None, device="meta")
    linear.weight = nn.Parameter(weight, requires_grad=False)
    if bias is not None:
        linear.bias = nn.Parameter(bias, requires_grad=False)
    return linear


def _embedding_name(model: nn.Module, embedding: nn.Module) -> str:
    for name, module in model.named_modules():
        if name and module is embedding and type(module) is nn.Embedding:
            return name
    raise ValueError("Expected the input word embedding to be an nn.Embedding submodule")


def _has_quantized_feed_forward(module: nn.Module) -> bool:
    return isinstance(module, nn.TransformerEncoderLayer) and any(
        isinstance(linear, QuantizedLinear) for linear in (module.linear1, module.linear2)
    )


def _keep_unfused(_module: nn.Module, _inputs: tuple) -> None:
    """A forward pre-hook makes PyTorch call the layer's individual modules."""


def _configure_transformers(model: nn.Module) -> None:
    # The fused layer and nested-tensor encoder paths inspect Linear.weight as a tensor.
    for module in model.modules():
        if _has_quantized_feed_forward(module):
            module.register_forward_pre_hook(_keep_unfused)
        elif isinstance(module, nn.TransformerEncoder) and any(
            _has_quantized_feed_forward(layer) for layer in module.layers
        ):
            module.use_nested_tensor = False


def quantize_weights(model: nn.Module, embedding: nn.Module) -> None:
    """Convert the CPU linear layers and input word table in place."""
    name = _embedding_name(model, embedding)
    # Relative-position tables can be read as tensors by the encoder.
    with _preserve_engine() as backend:
        engines = _engine_preferences("", backend.supported_engines)
        if backend.engine not in engines:
            backend.engine = engines[0]
        quantize_dynamic(
            model.eval(),
            {nn.Linear: default_dynamic_qconfig, name: float_qparams_weight_only_qconfig},
            inplace=True,
        )
    _configure_transformers(model)


def load_quantized_weights(
    model: nn.Module,
    embedding: nn.Module,
    path: Path,
    *,
    float_activation_pattern: re.Pattern[str] | None = None,
) -> QuantizationRuntime:
    """Install int8 modules in a new model and restore the saved state.

    Load a fresh model from the checkpoint folder instead of copying or pickling the
    loaded model or reloading its state, since repacking uses the caller's engine
    while the modules retain their activation range.
    """
    mixed = float_activation_pattern is not None
    embedding_name = _embedding_name(model, embedding)
    state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)

    with _preserve_engine() as backend:
        machine = platform.machine() if mixed else ""
        engines = _engine_preferences(machine, backend.supported_engines)
        caller = backend.engine
        if not mixed and caller in engines:
            engines = (caller, *(engine for engine in engines if engine != caller))
        # Probe before replacing modules so the untouched checkpoint can use any candidate.
        engine, full_range = _select_load_engine(engines, mixed)
        runtime = _pack_weights(
            model, embedding_name, state, engine, full_range, float_activation_pattern
        )

    _configure_transformers(model)
    model.eval()
    return runtime


def _pack_weights(
    model: nn.Module,
    embedding_name: str,
    state: dict,
    engine: str,
    full_range: bool,
    float_activation_pattern: re.Pattern[str] | None,
) -> QuantizationRuntime:
    float_layers = {}
    dynamic_layers = []
    for name, module in list(model.named_modules()):
        if type(module) is nn.Linear:
            keep_float = (
                float_activation_pattern is not None and float_activation_pattern.fullmatch(name)
            )
            linear_type = (
                _ActivationRangeLinear
                if float_activation_pattern is not None and not keep_float
                else QuantizedLinear
            )
            replacement = linear_type(
                module.in_features, module.out_features, bias_=module.bias is not None
            )
            if keep_float:
                float_layers[name] = replacement
            elif isinstance(replacement, _ActivationRangeLinear):
                dynamic_layers.append(replacement)
        elif name == embedding_name:
            weight = state[f"{name}._packed_params._packed_weight"]
            replacement = QuantizedEmbedding(weight.size(0), module.embedding_dim, _weight=weight)
        else:
            continue
        model.set_submodule(name, replacement)
    model.load_state_dict(state, strict=True)
    full_range = engine == "qnnpack" or (bool(dynamic_layers) and full_range)
    if full_range:
        for module in dynamic_layers:
            module.reduce_range = False
    for name, module in float_layers.items():
        model.set_submodule(name, _float_linear(module))
    activation_range = "full" if full_range else "reduced"
    return QuantizationRuntime(engine, activation_range, len(float_layers))
