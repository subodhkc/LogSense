#!/usr/bin/env python
"""
Minimal LoRA SFT for Phi-2.
Usage:
  accelerate launch scripts/train_phi2_lora.py \
    --data data/training/phi2_pairs.jsonl --epochs 1 --lr 2e-4 --batch 1 \
    --quantization 8bit --output adapters/phi2-lora
"""
from __future__ import annotations
import os, json, random
from dataclasses import dataclass
from typing import List

import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig

DEFAULT_MODEL = os.getenv("MODEL_NAME", "microsoft/phi-2")

@dataclass
class Args:
    data: str
    epochs: int = 1
    lr: float = 2e-4
    batch: int = 1
    quantization: str = "none"  # none|8bit|4bit
    output: str = "adapters/phi2-lora"


def parse_args() -> Args:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--quantization", choices=["none", "8bit", "4bit"], default="none")
    ap.add_argument("--output", default="adapters/phi2-lora")
    a = ap.parse_args()
    return Args(a.data, a.epochs, a.lr, a.batch, a.quantization, a.output)


def maybe_quantize(model, quantization: str):
    q = (quantization or "none").lower()
    if q == "8bit":
        try:
            import bitsandbytes  # noqa: F401
            model = AutoModelForCausalLM.from_pretrained(DEFAULT_MODEL, load_in_8bit=True, device_map="auto")
        except Exception:
            model = AutoModelForCausalLM.from_pretrained(DEFAULT_MODEL, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32, device_map="auto")
    elif q == "4bit":
        try:
            import bitsandbytes  # noqa: F401
            model = AutoModelForCausalLM.from_pretrained(DEFAULT_MODEL, load_in_4bit=True, device_map="auto")
        except Exception:
            model = AutoModelForCausalLM.from_pretrained(DEFAULT_MODEL, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32, device_map="auto")
    else:
        model = AutoModelForCausalLM.from_pretrained(DEFAULT_MODEL, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32, device_map="auto")
    return model


def main():
    args = parse_args()
    tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = maybe_quantize(None, args.quantization)

    # Prepare LoRA
    lora_cfg = LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05, bias="none", target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    model = get_peft_model(model, lora_cfg)

    # Load JSONL as HF dataset
    ds = load_dataset("json", data_files=args.data, split="train")
    ds = ds.train_test_split(test_size=0.1, seed=42)

    def format_example(ex):
        return f"Prompt:\n{ex['prompt']}\n\nAnswer:\n{ex['response']}"

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds["train"],
        eval_dataset=ds["test"],
        peft_config=lora_cfg,
        args=SFTConfig(
            output_dir=args.output,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch,
            gradient_accumulation_steps=max(1, 8 // args.batch),
            learning_rate=args.lr,
            fp16=torch.cuda.is_available(),
            save_steps=50,
            logging_steps=10,
            eval_steps=100,
            save_total_limit=1,
            report_to=[],
        ),
        formatting_func=format_example,
        max_seq_length=1024,
        dataset_text_field=None,
        packing=False,
    )

    trainer.train()
    trainer.model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"Saved LoRA adapters to {args.output}")


if __name__ == "__main__":
    main()
