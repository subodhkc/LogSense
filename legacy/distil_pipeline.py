# legacy/distil_pipeline.py
# Kept for one release for rollback purposes.
from __future__ import annotations
import logging

logger = logging.getLogger("legacy_distil")

try:
    from transformers import pipeline
    _pipe = pipeline("text-generation", model="distilgpt2", model_kwargs={"pad_token_id": 50256})
except Exception as e:
    logger.warning(f"Legacy DistilGPT-2 pipeline unavailable: {e}")
    _pipe = None


def legacy_generate(prompt: str, max_new_tokens: int = 200) -> str:
    if not _pipe:
        return "[legacy-distil] Offline model not available."
    out = _pipe(prompt, max_new_tokens=max_new_tokens)[0]["generated_text"]
    # simple echo removal
    if out.startswith(prompt):
        out = out[len(prompt):]
    return out.strip()
