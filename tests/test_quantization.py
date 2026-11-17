import pytest

torch = pytest.importorskip("torch")

from torch import nn  # noqa: E402

from pii_anonymizer.quantization import load_quantized_weights, quantize_weights  # noqa: E402


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
