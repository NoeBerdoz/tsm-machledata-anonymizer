import platform
import re

import pytest

torch = pytest.importorskip("torch")

from torch import nn  # noqa: E402

from pii_anonymizer import quantization  # noqa: E402
from pii_anonymizer.quantization import load_quantized_weights, quantize_weights  # noqa: E402

PROJECTION = "encoder.encoder.layer.0.output.dense"
ENGINES = [engine for engine in torch.backends.quantized.supported_engines if engine != "none"]
QNNPACK_FALLBACK = next((engine for engine in ENGINES if engine != "qnnpack"), None)
ISOLATE_ENGINE = pytest.mark.usefixtures("isolate_quantized_engine")


class FeedForwardBlock(nn.Module):
    def __init__(self):
        super().__init__()
        self.output = nn.Module()
        self.output.dense = nn.Linear(2, 1, bias=False)


class OutlierModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.word = nn.Embedding(2, 2)
        self.head = nn.Linear(2, 2, bias=False)
        self.encoder = nn.Module()
        self.encoder.encoder = nn.Module()
        self.encoder.encoder.layer = nn.ModuleList([FeedForwardBlock()])

    def forward(self, tokens):
        return self.encoder.encoder.layer[0].output.dense(self.word(tokens))


@pytest.mark.parametrize(
    ("machine", "supported", "expected"),
    [
        ("AMD64", ("x86", "onednn"), ("onednn", "x86")),
        ("x86_64", ("qnnpack", "x86", "fbgemm", "onednn"), ("onednn", "x86", "fbgemm", "qnnpack")),
        ("x86_64", ("qnnpack", "x86", "fbgemm"), ("x86", "fbgemm", "qnnpack")),
        ("aarch64", ("qnnpack", "onednn"), ("qnnpack", "onednn")),
        ("arm64", ("qnnpack",), ("qnnpack",)),
    ],
)
def test_engine_preferences(machine, supported, expected):
    assert quantization._engine_preferences(machine, supported) == expected


def test_engine_preferences_requires_usable_engine():
    with pytest.raises(RuntimeError, match="No supported PyTorch CPU quantization engine"):
        quantization._engine_preferences("x86_64", ("none",))


def _outlier_checkpoint(tmp_path):
    model = OutlierModel().eval()
    with torch.no_grad():
        model.word.weight.copy_(torch.tensor([[0.07, 0.0], [0.0, 65.0]]))
        model.encoder.encoder.layer[0].output.dense.weight.copy_(torch.tensor([[1.0, 0.0]]))
        model.head.weight.copy_(torch.tensor([[1.0, 0.0], [1.0, 1.0]]))
    tokens = torch.tensor([[0, 1]])
    expected = model(tokens).detach()
    quantize_weights(model, model.word)
    path = tmp_path / "weights.pt"
    torch.save(model.state_dict(), path)
    saved = torch.load(path, weights_only=True)
    key = f"{PROJECTION}._packed_params._packed_params"
    assert saved[key][0].dtype == torch.qint8
    return path, tokens, expected


def _load_outlier(path):
    loaded = OutlierModel()
    runtime = load_quantized_weights(
        loaded, loaded.word, path, float_activation_pattern=re.compile(re.escape(PROJECTION))
    )
    return loaded, runtime


def _head_crossing(model):
    return model.head(torch.tensor([[0.75, 0.0], [0.0, 255.0]]))[0, 0].item()


@pytest.fixture
def fresh_activation_probe():
    quantization._supports_full_range.cache_clear()
    yield
    quantization._supports_full_range.cache_clear()


@ISOLATE_ENGINE
@pytest.mark.parametrize("engine", ENGINES)
def test_small_signal_survives_int8_reload(tmp_path, monkeypatch, engine):
    path, tokens, expected = _outlier_checkpoint(tmp_path)
    monkeypatch.setattr(quantization, "_engine_preferences", lambda *_: (engine,))
    before = torch.backends.quantized.engine
    loaded, runtime = _load_outlier(path)
    assert torch.backends.quantized.engine == before
    torch.testing.assert_close(loaded(tokens), expected, rtol=0, atol=0.001)
    assert runtime.engine == engine
    assert runtime.float_activation_layers == 1
    assert type(loaded.encoder.encoder.layer[0].output.dense) is nn.Linear

    assert loaded.head.weight().dtype == torch.qint8
    assert (_head_crossing(loaded) > 0.5) == (runtime.activation_range == "full")
    pair_sum = loaded.head(torch.ones(1, 2))[0, 1].item()
    assert pair_sum == pytest.approx(2.0, abs=0.02)


@ISOLATE_ENGINE
@pytest.mark.parametrize("saturate_qnnpack", [False, True])
def test_default_loader_uses_preferred_engine_and_validated_crossing(
    tmp_path, monkeypatch, fresh_activation_probe, saturate_qnnpack
):
    path, _, _ = _outlier_checkpoint(tmp_path)
    backend = torch.backends.quantized
    if saturate_qnnpack:
        if "qnnpack" not in ENGINES:
            pytest.skip("QNNPACK unavailable")
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        native_linear = torch.ops.quantized.linear_dynamic

        def linear(inputs, packed, reduce_range=False):
            if backend.engine == "qnnpack" and inputs.shape == (1, 2) and not reduce_range:
                return torch.tensor([[1.011796]])
            return native_linear(inputs, packed, reduce_range=reduce_range)

        monkeypatch.setattr(torch.ops.quantized, "linear_dynamic", linear)

    engines = quantization._engine_preferences(platform.machine(), backend.supported_engines)
    caller = engines[-1]
    monkeypatch.setattr(backend, "engine", caller)
    preferred = None
    try:
        inputs = torch.ones(1, 2)
        weight = torch.quantize_per_tensor(inputs, 1 / 127, 0, torch.qint8)
        for engine in engines:
            backend.engine = engine
            try:
                packed = torch.ops.quantized.linear_prepack(weight, None)
                dot = torch.ops.quantized.linear_dynamic(inputs, packed, reduce_range=False).item()
            except RuntimeError:
                continue
            expect_full_range = abs(dot - 2.0) < 0.01
            if engine != "qnnpack" or expect_full_range:
                preferred = engine
                break
    finally:
        backend.engine = caller

    if preferred is None:
        with pytest.raises(RuntimeError, match="No usable PyTorch quantization engine"):
            _load_outlier(path)
    else:
        loaded, runtime = _load_outlier(path)
        assert runtime.engine == preferred
        assert (_head_crossing(loaded) > 0.5) == expect_full_range
    assert backend.engine == caller


@ISOLATE_ENGINE
def test_engine_is_restored_after_strict_load_error(tmp_path, monkeypatch):
    path, _, _ = _outlier_checkpoint(tmp_path)
    state = torch.load(path, weights_only=True)
    state["unexpected"] = torch.zeros(1)
    torch.save(state, path)

    backend = torch.backends.quantized
    engines = quantization._engine_preferences(platform.machine(), backend.supported_engines)
    caller = engines[-1]
    monkeypatch.setattr(backend, "engine", caller)
    with pytest.raises(RuntimeError, match="Unexpected key"):
        _load_outlier(path)
    assert backend.engine == caller


@ISOLATE_ENGINE
@pytest.mark.parametrize("engine", [engine for engine in ENGINES if engine != "qnnpack"])
def test_saturating_full_range_probe_uses_reduced_range(tmp_path, monkeypatch, engine):
    model = nn.Sequential(nn.Embedding(2, 2), nn.Linear(2, 1))
    quantize_weights(model, model[0])
    path = tmp_path / "weights.pt"
    torch.save(model.state_dict(), path)

    native_linear = torch.ops.quantized.linear_dynamic
    ranges = []

    def saturating_linear(x, packed, reduce_range=False):
        ranges.append(reduce_range)
        if not reduce_range:
            assert torch.equal(x, torch.ones(1, 2))
            return torch.full((1, 1), 1.011796)
        return native_linear(x, packed, reduce_range=True)

    monkeypatch.setattr(torch.ops.quantized, "linear_dynamic", saturating_linear)
    monkeypatch.setattr(quantization, "_engine_preferences", lambda *_: (engine,))
    quantization._supports_full_range.cache_clear()
    try:
        for _ in range(2):
            loaded = nn.Sequential(nn.Embedding(2, 2), nn.Linear(2, 1))
            runtime = load_quantized_weights(
                loaded, loaded[0], path, float_activation_pattern=re.compile("unused")
            )
            assert runtime.activation_range == "reduced"
            loaded(torch.tensor([[0, 1]]))
        assert ranges == [False, True, True]
    finally:
        quantization._supports_full_range.cache_clear()


@ISOLATE_ENGINE
@pytest.mark.skipif("qnnpack" not in ENGINES, reason="QNNPACK unavailable")
@pytest.mark.parametrize("failure", ["saturated", "prepack_error", "dynamic_error"])
@pytest.mark.parametrize(
    "allow_fallback",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(QNNPACK_FALLBACK is None, reason="QNNPACK is the only engine"),
        ),
    ],
)
def test_failed_qnnpack_check_uses_fallback_or_fails(
    tmp_path, monkeypatch, fresh_activation_probe, allow_fallback, failure
):
    path, _, _ = _outlier_checkpoint(tmp_path)
    fallback = QNNPACK_FALLBACK
    choices = ("qnnpack", fallback) if allow_fallback else ("qnnpack",)
    monkeypatch.setattr(quantization, "_engine_preferences", lambda *_: choices)
    checked = []
    backend = torch.backends.quantized
    before = backend.engine

    native_error = RuntimeError("Injected native quantization failure")
    native_prepack = torch.ops.quantized.linear_prepack
    native_linear = torch.ops.quantized.linear_dynamic

    def prepack(weight, bias):
        if backend.engine == "qnnpack" and failure == "prepack_error":
            checked.append(backend.engine)
            raise native_error
        return native_prepack(weight, bias)

    def linear(inputs, packed, reduce_range=False):
        if not reduce_range:
            assert torch.equal(inputs, torch.ones(1, 2))
            checked.append(backend.engine)
            if backend.engine == "qnnpack" and failure == "dynamic_error":
                raise native_error
            return torch.tensor([[1.011796]])
        return native_linear(inputs, packed, reduce_range=reduce_range)

    monkeypatch.setattr(torch.ops.quantized, "linear_prepack", prepack)
    monkeypatch.setattr(torch.ops.quantized, "linear_dynamic", linear)
    if allow_fallback:
        loaded, runtime = _load_outlier(path)
        assert (runtime.engine, runtime.activation_range) == (fallback, "reduced")
        assert _head_crossing(loaded) < 0.5
        assert checked == ["qnnpack", fallback]
    else:
        with pytest.raises(RuntimeError, match="No usable PyTorch quantization engine") as error:
            _load_outlier(path)
        assert "QNNPACK failed" in str(error.value)
        assert error.value.__cause__ is (None if failure == "saturated" else native_error)
        assert checked == ["qnnpack"]
    assert backend.engine == before


@ISOLATE_ENGINE
def test_activation_probe_accepts_roundoff(monkeypatch):
    backend = torch.backends.quantized
    with quantization._preserve_engine():
        backend.engine = ENGINES[0]
        monkeypatch.setattr(
            torch.ops.quantized, "linear_dynamic", lambda *args, **kwargs: torch.tensor([[1.995]])
        )
        quantization._supports_full_range.cache_clear()
        try:
            assert quantization._supports_full_range(backend.engine)
        finally:
            quantization._supports_full_range.cache_clear()


@ISOLATE_ENGINE
def test_int8_weights_round_trip(tmp_path):
    torch.manual_seed(7)
    model = nn.Sequential(nn.Embedding(12, 8), nn.Linear(8, 4))
    tokens = torch.tensor([[0, 1, 7, 11]])
    expected = model(tokens).detach()

    quantize_weights(model, model[0])
    path = tmp_path / "weights.pt"
    torch.save(model.state_dict(), path)
    state = torch.load(path, weights_only=True)
    embedding_key = "0._packed_params._packed_weight"
    assert embedding_key in state
    embedding = state[embedding_key]
    assert embedding.dtype == torch.quint8
    assert embedding.untyped_storage().nbytes() == 12 * 8
    assert [key for key, value in state.items() if getattr(value, "shape", None) == (12, 8)] == [
        embedding_key
    ]
    assert state["1._packed_params._packed_params"][0].dtype == torch.qint8

    reloaded = nn.Sequential(nn.Embedding(12, 8), nn.Linear(8, 4))
    load_quantized_weights(reloaded, reloaded[0], path)
    torch.testing.assert_close(reloaded(tokens), model(tokens), rtol=0, atol=0)
    torch.testing.assert_close(reloaded(tokens), expected, rtol=0, atol=0.03)
