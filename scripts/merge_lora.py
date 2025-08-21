#!/usr/bin/env python
from __future__ import annotations
import os
from transformers import AutoModelForCausalLM
from peft import PeftModel

BASE = os.getenv("MODEL_NAME", "microsoft/phi-2")
ADAPTER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "adapters", "phi2-lora")


def main():
    model = AutoModelForCausalLM.from_pretrained(BASE, device_map="auto")
    if os.path.isdir(ADAPTER):
        model = PeftModel.from_pretrained(model, ADAPTER)
        merged = model.merge_and_unload()
        out = os.path.join(os.path.dirname(ADAPTER), "phi2-merged")
        merged.save_pretrained(out)
        print(f"Merged to {out}")
    else:
        print("No adapter to merge; skipping")


if __name__ == "__main__":
    main()
