# Migration to Phi-2

- Model: `microsoft/phi-2` via Hugging Face Transformers.
- Replaces legacy DistilGPT-2 paths. Feature flag: `MODEL_BACKEND=phi2|legacy` (default: `phi2`).

## Install

```
pip install -r requirements.txt
```

Optional quantization:
```
pip install bitsandbytes  # not supported on Windows
```

## Inference

```
python -m modules.phi2_inference --smoke
```

## Training (LoRA)

```
python scripts/build_dataset.py
accelerate launch scripts/train_phi2_lora.py --data data/training/phi2_pairs.jsonl --epochs 1 --batch 1 --output adapters/phi2-lora
```

## Rollback
- Set `MODEL_BACKEND=legacy` to use the legacy code in `legacy/` for one release.
