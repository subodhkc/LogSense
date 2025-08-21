# tests/test_phi2_basic.py
from modules.phi2_inference import phi2_summarize

def test_phi2_completion_smoke():
    out = phi2_summarize("Summarize: BIOS updated then MSI failed.", max_tokens=16)
    assert isinstance(out, str)
    assert len(out) > 0
