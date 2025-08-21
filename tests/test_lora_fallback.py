import os
import types
import pytest

# We avoid loading real models by monkeypatching the base summarize

def test_lora_wrapper_calls_base_when_adapter_missing(monkeypatch):
    # Import inside test to ensure module-level adapter detection runs here
    from modules import phi2_inference_lora as lora

    captured = {}

    def fake_base_summarize(prompt: str, max_tokens: int = 200) -> str:
        captured["prompt"] = prompt
        captured["max_tokens"] = max_tokens
        return "OK"

    # Patch the base summarize used by the lora wrapper and bypass adapter loading
    monkeypatch.setattr(lora, "_base_summarize", fake_base_summarize)
    monkeypatch.setattr(lora, "_maybe_load_adapter", lambda: None)

    # Ensure default adapter path does not exist
    default_path = os.path.join(os.path.dirname(os.path.dirname(lora.__file__)), "adapters", "phi2-lora")
    if os.path.isdir(default_path):
        pytest.skip("Adapter exists on this machine; skip fallback test to avoid loading")

    out = lora.phi2_summarize("hello", max_tokens=5)
    
    # Verify the wrapper called base summarize with correct args
    assert captured["prompt"] == "hello"
    assert captured["max_tokens"] == 5
    assert out == "OK"
