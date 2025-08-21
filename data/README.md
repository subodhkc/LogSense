# Training Data Format

Store only approved/clean pairs. No raw PII.

File: `data/training/phi2_pairs.jsonl`
Each line JSON object:
{"prompt": "...", "response": "...", "tags": ["source:python"|"source:ai", "topic:rca|summary|timeline"]}

Sources scanned by `scripts/build_dataset.py`:
- `outputs/python_engines/` (structured rule-based outputs)
- `outputs/ai_engine/accepted/` (operator-approved AI outputs)

Run:
```
python scripts/build_dataset.py
```
