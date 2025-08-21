# SKC Log Reader (Phi‑2)

SKC Log Reader is a modular log analysis tool built with Python + Streamlit. It helps TPMs and QA engineers triage provisioning/installer logs (BIOS, SoftPaq, MSI, imaging, agents) and produces concise RCA with optional LLM assistance.



## 🔍 Key Features
- Upload ZIP logs and parse events across multiple files
- Structured Pre-AI RCA with error detection and rule-based recommendations
- Interactive timeline, test plan validation, log filtering
- Visuals via charts, clustering, decision trees, and anomaly detection (SVM)
- Redaction engine with built-in patterns for PII
- PDF report export (with visual summaries)
- Optional LLM-powered analysis (offline or via OpenAI API)

## 🧰 Setup

### 1. Clone and Setup
```bash
pip install -r requirements.txt
```

### 2. Run
```bash
streamlit run skc_log_analyzer.py
```

### 3. Folder Structure (condensed)
```
├── skc_log_analyzer.py
├── analysis.py
├── redaction.py
├── test_plan.py
├── recommendations.py
├── ai_rca.py                # Hybrid AI RCA (offline Phi‑2 + OpenAI fallback)
├── report.py
├── setup.py
├── clustering_model.py
├── decision_tree_model.py
├── anomaly_svm.py
├── utils.py
├── requirements.txt
├── plans/
│   ├── dash_test_plan.json
│   └── softpaq_test_plan.json
├── config/
│   ├── redact.json
│   └── model.yaml   # Phi‑2 config (model, generation params)
```



## 🔐 Security
- Only redacted logs are sent to any external API (if enabled)
- All parsing, analytics, and local LLM inference run locally

## 📦 Deployment
- Local: `streamlit run skc_log_analyzer.py`
- Docker (CPU): build with the provided `Dockerfile`

## 🧠 LLM Support (Phi‑2 Migration)
- Default offline model: Microsoft Phi‑2
- Optional LoRA adapters auto-load from `adapters/phi2-lora`
- OpenAI fallback supported if `OPENAI_API_KEY` is set

Env/config overrides (also see `config/model.yaml`):
- `MODEL_BACKEND`: `phi2` (default) or `legacy`
- `MODEL_NAME`: default `microsoft/phi-2` (CI uses a tiny model)
- `QUANTIZATION`: `none` | `8bit` | `4bit` (bitsandbytes; Linux recommended)
- `MAX_NEW_TOKENS`, `TEMPERATURE`, `TOP_P`, `REPETITION_PENALTY`

---




## UI Engine Toggles
- Use Python Engines (rules, validations, summaries)
- Use Local LLM (Phi‑2)
- Use Cloud AI (OpenAI)

These appear in the sidebar and control what is executed and rendered.

## Credits
Built by Subodh Kc
Powered by Python, Streamlit, Transformers, and open‑source intelligence
