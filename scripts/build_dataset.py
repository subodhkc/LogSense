#!/usr/bin/env python
from __future__ import annotations
import os, json, hashlib
from typing import List, Dict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC_PY = BASE / "outputs" / "python_engines"
SRC_AI = BASE / "outputs" / "ai_engine" / "accepted"
OUT_DIR = BASE / "data" / "training"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "phi2_pairs.jsonl"

MAX_LEN = 4096


def _norm_text(t: str) -> str:
    t = (t or "").strip()
    return " ".join(t.split())


def _hash_prompt(p: str) -> str:
    return hashlib.sha256(p.encode("utf-8")).hexdigest()


def _scan_dir(d: Path, source_tag: str) -> List[Dict]:
    pairs = []
    if not d.exists():
        return pairs
    for p in d.rglob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        prompt = _norm_text(data.get("prompt") or data.get("input") or "")[:MAX_LEN]
        resp = _norm_text(data.get("response") or data.get("output") or "")[:MAX_LEN]
        if not prompt or not resp:
            continue
        pairs.append({
            "prompt": prompt,
            "response": resp,
            "tags": [source_tag],
        })
    return pairs


def main():
    pairs = _scan_dir(SRC_PY, "source:python") + _scan_dir(SRC_AI, "source:ai")
    # Dedup by prompt hash
    seen = set()
    out = []
    for ex in pairs:
        h = _hash_prompt(ex["prompt"])
        if h in seen:
            continue
        seen.add(h)
        out.append(ex)
    # Simple tox check
    clean = []
    for ex in out:
        if "-----BEGIN PRIVATE KEY-----" in ex["prompt"] or "AKIA" in ex["prompt"]:
            continue
        clean.append(ex)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for ex in clean:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Wrote {len(clean)} pairs to {OUT_PATH}")


if __name__ == "__main__":
    main()
