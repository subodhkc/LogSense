# LogSense - Enterprise Log Analysis & RCA

LogSense is a professional, modular log analysis application built with Python and Streamlit. It helps TPMs, QA engineers, and support teams triage provisioning/installer logs (BIOS, SoftPaq, MSI, imaging, agents) and produce concise, defensible root[U+2011]cause analysis (RCA). AI assistance is available via local LLM or cloud.



## [SEARCH] Key Features
- Secure log ingestion (ZIP and single-file) with robust parsing
- Structured pre[U+2011]AI RCA: error detection, correlations, and rule[U+2011]based recommendations
- Interactive timeline, test plan validation, and focused log filtering
- Advanced analytics: clustering, anomaly detection (SVM), decision trees
- PII redaction engine with configurable patterns
- Professional PDF reporting with corporate SaaS design and executive one[U+2011]pager
- Optional AI analysis: local (offline) model or OpenAI fallback

## [U+1F9F0] Setup

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
[U+251C][U+2500][U+2500] skc_log_analyzer.py
[U+251C][U+2500][U+2500] analysis.py
[U+251C][U+2500][U+2500] redaction.py
[U+251C][U+2500][U+2500] test_plan.py
[U+251C][U+2500][U+2500] recommendations.py
[U+251C][U+2500][U+2500] ai_rca.py                # Hybrid AI RCA (offline Phi[U+2011]2 + OpenAI fallback)
[U+251C][U+2500][U+2500] report/                  # PDF report package (generate_pdf, pdf_builder)
[U+251C][U+2500][U+2500] setup.py
[U+251C][U+2500][U+2500] clustering_model.py
[U+251C][U+2500][U+2500] decision_tree_model.py
[U+251C][U+2500][U+2500] anomaly_svm.py
[U+251C][U+2500][U+2500] utils.py
[U+251C][U+2500][U+2500] requirements.txt
[U+251C][U+2500][U+2500] plans/
[U+2502]   [U+251C][U+2500][U+2500] dash_test_plan.json
[U+2502]   [U+2514][U+2500][U+2500] softpaq_test_plan.json
[U+251C][U+2500][U+2500] config/
[U+2502]   [U+251C][U+2500][U+2500] redact.json
[U+2502]   [U+2514][U+2500][U+2500] model.yaml   # Phi[U+2011]2 config (model, generation params)
```



## [U+1F510] Security
- Only redacted logs are sent to any external API (if enabled)
- All parsing, analytics, and local LLM inference run locally

## [U+1F4E6] Deployment
- Local: `streamlit run skc_log_analyzer.py`
- Docker (CPU): build with the provided `Dockerfile`

## [U+1F9E0] LLM Support (Phi[U+2011]2 Migration)
- Default offline model: Microsoft Phi[U+2011]2
- Optional LoRA adapters auto[U+2011]load from `adapters/phi2-lora`
- OpenAI fallback supported if `OPENAI_API_KEY` is set

Env/config overrides (also see `config/model.yaml`):
- `MODEL_BACKEND`: `phi2` (default) or `legacy`
- `MODEL_NAME`: default `microsoft/phi-2` (CI uses a tiny model)
- `QUANTIZATION`: `none` | `8bit` | `4bit` (bitsandbytes; Linux recommended)
- `MAX_NEW_TOKENS`, `TEMPERATURE`, `TOP_P`, `REPETITION_PENALTY`

---




## UI Engine Toggles
- Use Python Engines (rules, validations, summaries)
- Use Local LLM (Phi[U+2011]2)
- Use Cloud AI (OpenAI)

These appear in the sidebar and control what is executed and rendered.

## Credits
Built by Subodh Kc
Powered by Python, Streamlit, Transformers, and open[U+2011]source intelligence