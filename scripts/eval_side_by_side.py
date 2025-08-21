#!/usr/bin/env python
from __future__ import annotations
import os, csv, time
from typing import List

from modules.phi2_inference import phi2_summarize as phi2_base
from modules.phi2_inference_lora import phi2_summarize as phi2_lora

try:
    from legacy.distil_pipeline import legacy_generate as distil
except Exception:
    distil = None


def eval_samples(samples: List[str]):
    rows = []
    for s in samples:
        start = time.time(); a = distil(s, 64) if distil else ""; t_a = time.time()-start
        start = time.time(); b = phi2_base(s, 64); t_b = time.time()-start
        start = time.time(); c = phi2_lora(s, 64); t_c = time.time()-start
        rows.append({
            "prompt": s,
            "legacy_distil": a,
            "phi2_base": b,
            "phi2_lora": c,
            "lat_ms_legacy": int(t_a*1000),
            "lat_ms_phi2": int(t_b*1000),
            "lat_ms_phi2_lora": int(t_c*1000),
        })
    return rows


def main():
    samples = [
        "Summarize: BIOS updated then MSI Validate failed due to missing DLL.",
        "RCA: EVTX shows driver crash followed by service restart loop.",
    ]
    rows = eval_samples(samples)
    os.makedirs("reports", exist_ok=True)
    out = os.path.join("reports", "side_by_side.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
