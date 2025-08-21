# LoRA Training for Phi-2

Data format: JSONL with fields:
{"prompt": "...", "response": "...", "tags": ["source:python"|"source:ai", "topic:rca|summary|timeline"]}

1) Build dataset
```
python scripts/build_dataset.py
```

2) Fine-tune
```
accelerate launch scripts/train_phi2_lora.py --data data/training/phi2_pairs.jsonl --epochs 1 --batch 1 --output adapters/phi2-lora
```

3) Inference with adapters
- `modules/phi2_inference_lora.py` auto-loads from `adapters/phi2-lora` if present.
