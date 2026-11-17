"""PyTorch CPU quantization for linear layers and a word embedding."""

from pathlib import Path

import torch
from torch import nn
from torch.ao.nn.quantized import Embedding as QuantizedEmbedding
from torch.ao.nn.quantized.dynamic import Linear as QuantizedLinear
from torch.ao.quantization import (
    default_dynamic_qconfig,
    float_qparams_weight_only_qconfig,
    quantize_dynamic,
)


def _select_engine() -> None:
    backend = torch.backends.quantized
    supported = backend.supported_engines
    engines = ("x86", "fbgemm", "qnnpack")
    if backend.engine in engines:
        return
    for engine in engines:
        if engine in supported:
            backend.engine = engine
            return
    raise RuntimeError(f"No supported PyTorch CPU quantization engine in {supported}")


def _embedding_name(model: nn.Module, embedding: nn.Module) -> str:
    for name, module in model.named_modules():
        if name and module is embedding and type(module) is nn.Embedding:
            return name
    raise ValueError("Expected the input word embedding to be an nn.Embedding submodule")


def _has_quantized_feed_forward(module: nn.Module) -> bool:
    return isinstance(module, nn.TransformerEncoderLayer) and isinstance(
        module.linear1, QuantizedLinear
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
    _select_engine()
    name = _embedding_name(model, embedding)
    # Relative-position tables can be read as tensors by the encoder.
    quantize_dynamic(
        model.eval(),
        {nn.Linear: default_dynamic_qconfig, name: float_qparams_weight_only_qconfig},
        inplace=True,
    )
    _configure_transformers(model)


def load_quantized_weights(model: nn.Module, embedding: nn.Module, path: Path) -> None:
    """Install int8 modules in a new model and restore the saved state."""
    _select_engine()
    embedding_name = _embedding_name(model, embedding)
    state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    for name, module in list(model.named_modules()):
        if type(module) is nn.Linear:
            replacement = QuantizedLinear(
                module.in_features, module.out_features, bias_=module.bias is not None
            )
        elif name == embedding_name:
            weight = state[f"{name}._packed_params._packed_weight"]
            replacement = QuantizedEmbedding(weight.size(0), module.embedding_dim, _weight=weight)
        else:
            continue
        model.set_submodule(name, replacement)
    model.load_state_dict(state, strict=True)
    _configure_transformers(model)
    model.eval()
