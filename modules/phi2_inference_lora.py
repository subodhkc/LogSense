# modules/phi2_inference_lora.py
from __future__ import annotations
import os
from typing import Optional
from .phi2_inference import _ensure_model, _tokenizer, _model, phi2_summarize as _base_summarize, _model_id
from peft import PeftModel
import logging

logger = logging.getLogger("phi2_inference_lora")

_adapter_loaded = False
_adapter_id = None


def _maybe_load_adapter(path: Optional[str] = None):
    global _adapter_loaded, _adapter_id
    if _adapter_loaded:
        return
    _ensure_model()
    path = path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "adapters", "phi2-lora")
    if os.path.isdir(path):
        try:
            logger.info(f"Loading LoRA adapter from {path}...")
            # Wrap base model
            from .phi2_inference import _model as base_model
            peft_model = PeftModel.from_pretrained(base_model, path)
            # Monkey-patch base model reference and adapter id (for cache keys)
            from . import phi2_inference as base
            base._model = peft_model
            base._adapter_id = path
            _adapter_id = path
            _adapter_loaded = True
        except Exception as e:
            logger.warning(f"Failed to load LoRA adapter: {e}")


def phi2_summarize(prompt: str, max_tokens: int = 200) -> str:
    _maybe_load_adapter()
    return _base_summarize(prompt, max_tokens)
