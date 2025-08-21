# modules/phi2_inference.py
from __future__ import annotations
import os, json, hashlib, time, logging
from typing import Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import yaml

logger = logging.getLogger("phi2_inference")
logging.basicConfig(level=logging.INFO)

DEFAULT_CFG = {
    "model_name": "microsoft/phi-2",
    "quantization": "none",
    "max_new_tokens": 200,
    "temperature": 0.7,
    "top_p": 0.95,
    "repetition_penalty": 1.2,
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "model.yaml")
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache", "inference")
os.makedirs(CACHE_DIR, exist_ok=True)

_tokenizer = None
_model = None
_model_id = None
_adapter_id = None
_device = None


def _load_config() -> dict:
    """Load and validate model configuration from YAML and environment variables."""
    cfg = DEFAULT_CFG.copy()
    
    # Load from YAML file with error handling
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                # Only update known config keys
                cfg.update({k: v for k, v in loaded.items() if k in DEFAULT_CFG})
        except (yaml.YAMLError, IOError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to load config from {CONFIG_PATH}: {e}. Using defaults.")
    
    # Environment variable overrides with validation
    cfg["model_name"] = os.getenv("MODEL_NAME", cfg["model_name"])
    cfg["quantization"] = os.getenv("QUANTIZATION", cfg["quantization"]).lower()
    
    # Validate quantization option
    if cfg["quantization"] not in ("none", "8bit", "4bit"):
        logger.warning(f"Invalid quantization '{cfg['quantization']}', using 'none'")
        cfg["quantization"] = "none"
    
    # Integer parameters with validation
    for k in ("max_new_tokens",):
        if os.getenv(k.upper()):
            try:
                cfg[k] = max(1, int(os.getenv(k.upper())))
            except ValueError:
                logger.warning(f"Invalid {k} value, using default {cfg[k]}")
    
    # Float parameters with validation
    for k in ("temperature", "top_p", "repetition_penalty"):
        if os.getenv(k.upper()):
            try:
                val = float(os.getenv(k.upper()))
                if k == "temperature" and 0 <= val <= 2.0:
                    cfg[k] = val
                elif k == "top_p" and 0 <= val <= 1.0:
                    cfg[k] = val
                elif k == "repetition_penalty" and val >= 1.0:
                    cfg[k] = val
                else:
                    logger.warning(f"Invalid {k} value {val}, using default {cfg[k]}")
            except ValueError:
                logger.warning(f"Invalid {k} value, using default {cfg[k]}")
    
    return cfg


def _maybe_quantization_args(quantization: str) -> dict:
    q = quantization.lower()
    if q == "8bit":
        try:
            import bitsandbytes  # noqa: F401
            return {"load_in_8bit": True}
        except Exception:
            logger.warning("8-bit quantization requested but bitsandbytes not available; using full precision.")
            return {}
    if q == "4bit":
        try:
            import bitsandbytes  # noqa: F401
            return {
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": torch.float16,
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            }
        except Exception:
            logger.warning("4-bit quantization requested but bitsandbytes not available; using full precision.")
            return {}
    return {}


def _ensure_model():
    global _tokenizer, _model, _model_id, _device
    if _model is not None:
        return
    cfg = _load_config()
    model_name = cfg["model_name"]
    qargs = _maybe_quantization_args(cfg.get("quantization", "none"))

    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device_map = "auto"

    logger.info(f"Loading Phi-2 model '{model_name}' (dtype={torch_dtype}, quant={cfg.get('quantization')})...")
    _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token
    _model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch_dtype,
        device_map=device_map,
        trust_remote_code=True,
        **qargs,
    )
    _model_id = model_name
    _device = "cuda" if torch.cuda.is_available() else "cpu"


def _cache_key(prompt: str, model_id: str, adapter_id: Optional[str], generation_params: dict = None) -> str:
    h = hashlib.sha256()
    h.update(prompt.encode("utf-8"))
    h.update(model_id.encode("utf-8"))
    h.update((adapter_id or "").encode("utf-8"))
    if generation_params:
        # Include generation params in cache key to avoid collisions
        params_str = json.dumps(generation_params, sort_keys=True)
        h.update(params_str.encode("utf-8"))
    return h.hexdigest()


def _cache_get(key: str) -> Optional[str]:
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("text")
        except Exception:
            return None
    return None


def _cache_put(key: str, text: str) -> None:
    path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"text": text}, f)


def phi2_summarize(prompt: str, max_tokens: int = 200) -> str:
    """Generate completion using Phi-2. Removes prompt echo and returns trimmed text."""
    _ensure_model()
    cfg = _load_config()
    max_new = min(max_tokens, int(cfg.get("max_new_tokens", 200)))

    # Cache read with generation params
    gen_params = {
        "max_new_tokens": max_new,
        "temperature": float(cfg.get("temperature", 0.7)),
        "top_p": float(cfg.get("top_p", 0.95)),
        "repetition_penalty": float(cfg.get("repetition_penalty", 1.2))
    }
    key = _cache_key(prompt, _model_id, _adapter_id, gen_params)
    cached = _cache_get(key)
    if cached is not None:
        logger.info("phi2_summarize: cache_hit=true")
        return cached

    start = time.time()
    input_ids = _tokenizer(prompt, return_tensors="pt").to(_model.device)
    gen_ids = _model.generate(
        **input_ids,
        max_new_tokens=max_new,
        do_sample=True,
        temperature=float(cfg.get("temperature", 0.7)),
        top_p=float(cfg.get("top_p", 0.95)),
        repetition_penalty=float(cfg.get("repetition_penalty", 1.2)),
        pad_token_id=_tokenizer.eos_token_id,
        eos_token_id=_tokenizer.eos_token_id,
    )
    text = _tokenizer.decode(gen_ids[0], skip_special_tokens=True)
    # Remove prompt echo
    if text.startswith(prompt):
        text = text[len(prompt):]
    text = text.strip()

    latency = (time.time() - start) * 1000
    logger.info(f"phi2_summarize: model_id={_model_id} device={_device} quant={_load_config().get('quantization')} latency_ms={latency:.1f}")

    # Cache write
    _cache_put(key, text)
    return text


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        print(phi2_summarize("Summarize: The system installed BIOS then rebooted; errors occurred in MSI action 'Validate'."))
        print("[SMOKE OK]")
