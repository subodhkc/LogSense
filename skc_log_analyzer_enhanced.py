# Streamlit UI and orchestration for LogSense (Enhanced Corporate UX)

import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import streamlit as st
import pandas as pd
import zipfile, io
from io import BytesIO
from dotenv import load_dotenv
import tempfile
from datetime import datetime

# Analysis modules
from analysis.templates import TemplateExtractor
from report.pdf_builder import build_pdf as build_onepager_pdf
from analysis.event_chain import ChainSpec, detect_sequences
from analysis.session import correlate_start_end
from datamodels.events import Event as CanonEvent

# Core modules
import analysis
import redaction
import test_plan
import charts
import recommendations
import ai_rca
import report
import setup
import clustering_model
import decision_tree_model
import anomaly_svm
from rca_rules import get_all_rca_summaries

# UI Components
from ui_components import (
    render_header, render_progress_indicator, render_info_card,
    render_metric_cards, render_status_badge, render_data_table,
    render_action_buttons, render_sidebar_config, render_welcome_screen
)

# --- Helpers: adapters to canonical Event model ---
def _to_dt(obj):
    try:
        if isinstance(obj, datetime):
            return obj
        return datetime.fromisoformat(str(obj))
    except Exception:
        return None

def adapt_events_to_canonical(evts):
    canon = []
    for ev in evts:
        ts = _to_dt(getattr(ev, 'timestamp', None))
        source = getattr(ev, 'component', None) or getattr(ev, 'source', 'text')
        level = getattr(ev, 'severity', None) or getattr(ev, 'level', None)
        msg = getattr(ev, 'message', '')
        canon.append(CanonEvent(ts=ts, source=str(source), level=(str(level) if level else None),
                                event_id=None, message=str(msg), meta={}, tags=[]))
    return canon

# Load environment variables
load_dotenv()

# App metadata
st.set_page_config(
    page_title="LogSense - Enterprise Log Analysis",
    page_icon="[U+1F9ED]",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state["session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
if "current_step" not in st.session_state:
    st.session_state["current_step"] = 0
if "files_processed" not in st.session_state:
    st.session_state["files_processed"] = 0
if "events_analyzed" not in st.session_state:
    st.session_state["events_analyzed"] = 0
if "issues_found" not in st.session_state:
    st.session_state["issues_found"] = 0

# Render sidebar configuration
engines, analysis_settings = render_sidebar_config()
use_python_eng = engines["python"]
use_local_llm = engines["local_llm"]
use_cloud_ai = engines["cloud_ai"]

# --- Welcome Screen ---
if "show_welcome" not in st.session_state:
    st.session_state["show_welcome"] = True

if st.session_state["show_welcome"]:
    render_welcome_screen()
    st.stop()

# --- Main Interface ---
render_header()
render_progress_indicator(st.session_state["current_step"])

# User Information Section
with st.expander("[U+1F464] User & Test Information", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.text_input("Your Name", placeholder="Enter your full name", help="This will appear in your final report.")
        app_name = st.text_input("Application Being Tested", placeholder="e.g., HP Power Manager", help="Used to focus log filtering and reporting.")
    with col2:
        app_version = st.text_input("Application Version", placeholder="e.g., v2.1.3 or Build 12345", help="Version of the application being tested")
        test_environment = st.selectbox("Test Environment", ["Production", "Staging", "Development", "QA", "Pre-production", "Other"], help="Environment where testing occurred")

# Issue Description Section
with st.expander("[SEARCH] Issue Description & Context", expanded=True):
    issue_description = st.text_area(
        "Describe the Issue", 
        placeholder="What problem are you experiencing? Be specific about symptoms, error messages, and impact.",
        height=100,
        help="Detailed description helps AI provide better root cause analysis"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        deployment_method = st.selectbox("Deployment Method", ["DASH Imaging", "SoftPaq Installation", "Manual Install", "Group Policy", "SCCM", "Other"])
        build_changes = st.text_area("Recent Changes", placeholder="Any recent updates, patches, or configuration changes", height=60)
    with col2:
        build_number = st.text_input("Build/Version Number", placeholder="e.g., 26000.1000")
        previous_version = st.text_input("Previous Working Version", placeholder="Last known good version")

# File Upload Section
with st.expander("[U+1F4C1] Log File Upload", expanded=True):
    uploaded_file = st.file_uploader(
        "Upload Log Files (ZIP recommended)", 
        type=["zip", "txt", "log"], 
        help="Upload a ZIP file containing multiple logs, or individual log files."
    )
    
    events = []
    redacted_events = []
    redacted_metadata = {}
    
    if uploaded_file is not None:
        st.session_state["current_step"] = 1
        
        with st.spinner("Processing uploaded files..."):
            if uploaded_file.name.endswith('.zip'):
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    zip_contents = zip_ref.namelist()
                    log_files = [f for f in zip_contents if f.endswith(('.txt', '.log'))]
                    
                    render_info_card(
                        "Archive Contents", 
                        f"Found {len(log_files)} log files in ZIP archive ({len(zip_contents)} total files)",
                        "[U+1F4C1]"
                    )
                    
                    for file_name in log_files:
                        with zip_ref.open(file_name) as file:
                            content = file.read().decode('utf-8', errors='ignore')
                            file_events = analysis.parse_logs(content)
                            events.extend(file_events)
            else:
                content = uploaded_file.read().decode('utf-8', errors='ignore')
                events = analysis.parse_logs(content)
        
        st.session_state["files_processed"] = 1 if not uploaded_file.name.endswith('.zip') else len(log_files)
        st.session_state["events_analyzed"] = len(events)
        
        render_status_badge("success", f"Processed {len(events)} log events")
        
        # Apply redaction
        with st.spinner("Applying redaction patterns..."):
            redacted_events, redacted_metadata = redaction.apply_redaction(events, {})
        
        render_status_badge("success", f"Redaction complete. {len(redacted_events)} events processed.")
        st.session_state["current_step"] = 2

# Only show analysis sections if we have data
if redacted_events:
    st.session_state["current_step"] = 3
    
    # Key metrics
    issues = [ev for ev in redacted_events if ev.severity in ["ERROR", "CRITICAL", "WARNING"]]
    st.session_state["issues_found"] = len(issues)
    
    render_metric_cards({
        "Total Events": len(redacted_events),
        "Issues Found": len(issues),
        "Files Processed": st.session_state["files_processed"],
        "Critical Errors": len([ev for ev in issues if ev.severity == "CRITICAL"])
    })

    # Build user context for AI
    user_context = {
        "user_name": user_name,
        "app_name": app_name,
        "app_version": app_version,
        "test_environment": test_environment,
        "deployment_method": deployment_method,
        "build_changes": build_changes,
        "build_number": build_number,
        "previous_version": previous_version,
        "issue_description": issue_description,
    }

    # Test Plan Section
    if use_python_eng:
        with st.expander("[U+1F4CB] Test Plan Validation", expanded=False):
            available_plans = setup.get_available_test_plans()
            if available_plans:
                # Friendly mapping similar to primary UI
                plan_labels = {}
                for fn in available_plans:
                    low = fn.lower()
                    if "softpaq" in low:
                        plan_labels[fn] = "SoftPaq (SP/DASH Installer)"
                    elif "dash" in low or "pulsar" in low or "factory" in low:
                        plan_labels[fn] = "Factory Image (Pulsar/DASH)"
                    else:
                        plan_labels[fn] = fn

                display_options = ["None"] + [f"{plan_labels[fn]} - {fn}" for fn in available_plans]
                sel = st.selectbox("Select Test Plan", display_options)
                if sel != "None":
                    try:
                        selected_plan_file = sel.split(" - ", 1)[1]
                    except Exception:
                        selected_plan_file = sel
                    plan_data = setup.get_test_plan(selected_plan_file)
                    if plan_data:
                        friendly_name = plan_labels.get(selected_plan_file, selected_plan_file)
                        rich_result = test_plan.validate_plan(plan_data, events, plan_name=friendly_name)
                        st.session_state["validation_result"] = rich_result
                        if rich_result and rich_result.get("steps"):
                            df = pd.DataFrame([
                                {
                                    "Step": s.get("Step"),
                                    "Action": s.get("Step Action"),
                                    "Expected": s.get("Expected Result"),
                                    "Status": s.get("Status"),
                                    "Phase": s.get("phase"),
                                    "First Hit": s.get("first_hit_time"),
                                    "Last Hit": s.get("last_hit_time"),
                                }
                                for s in rich_result["steps"]
                            ])
                            render_data_table(df, "Test Results")
                        else:
                            st.info("No test plan results available.")
                    else:
                        st.error("Failed to load selected test plan.")
            else:
                st.info("No test plans available in the plans/ directory.")

    # Timeline and Issues
    st.subheader("[U+1F4CA] Timeline & Issues Analysis")
    
    # Timeline
    timeline_events = sorted(redacted_events, key=lambda x: x.timestamp)[:50]  # Show first 50
    timeline_df = pd.DataFrame([{
        "Timestamp": str(ev.timestamp),
        "Component": ev.component,
        "Severity": ev.severity,
        "Message": ev.message[:100] + "..." if len(ev.message) > 100 else ev.message
    } for ev in timeline_events])
    
    render_data_table(timeline_df, "Event Timeline")

    # Issues Summary
    if issues:
        issues_df = pd.DataFrame([{
            "Timestamp": str(ev.timestamp),
            "Component": ev.component,
            "Severity": ev.severity,
            "Message": ev.message
        } for ev in issues])
        render_data_table(issues_df, "Errors and Warnings")
    else:
        render_info_card("No Issues Found", "No warnings or errors detected in the logs.", "[OK]", "#d4edda")

    # Tabs for advanced analysis
    tab_templates, tab_ml, tab_corr, tab_reports = st.tabs(["Templates", "ML Insights", "Correlations", "Reports"])

    with tab_templates:
        if st.checkbox("Show Templates (Structural Patterns)", value=False):
            st.subheader("Templates (Structural Patterns)")
            with st.spinner("Mining templates..."):
                canon_all = adapt_events_to_canonical(redacted_events)
                tmpl = TemplateExtractor()
                assigned = tmpl.assign(canon_all)
                summary_rows = tmpl.summary()
            if summary_rows:
                tmpl_df = pd.DataFrame([{"Template ID": tid, "Count": cnt, "Template": tpl} for tid, cnt, tpl in summary_rows])
                render_data_table(tmpl_df, "Template Analysis")

    with tab_ml:
        st.subheader("[U+1F916] Machine Learning Insights")
        render_info_card(
            "ML Analysis",
            "Use machine learning to uncover hidden patterns: clustering, anomaly detection, and severity prediction.",
            "[U+1F52C]"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Run Clustering", use_container_width=True):
                with st.spinner("Clustering events..."):
                    cluster_fig = clustering_model.cluster_events(events)
                    if cluster_fig:
                        st.pyplot(cluster_fig)

        with col2:
            if st.button("Severity Prediction", use_container_width=True):
                with st.spinner("Analyzing severity predictions..."):
                    severity_fig = decision_tree_model.analyze_event_severity(events)
                    if severity_fig:
                        st.pyplot(severity_fig)

        with col3:
            if st.button("Anomaly Detection", use_container_width=True):
                with st.spinner("Detecting anomalies..."):
                    anomaly_fig = anomaly_svm.detect_anomalies(events)
                    if anomaly_fig:
                        st.pyplot(anomaly_fig)

    with tab_corr:
        if st.checkbox("Show Correlations (Sequences & Sessions)", value=False):
            st.subheader("Correlations")
            with st.spinner("Detecting common sequences and sessions..."):
                canon_all = adapt_events_to_canonical(redacted_events)
                spec = ChainSpec(steps=[{"level": "WARN"}, {"level": "ERROR"}], window_sec=300)
                chain_hits = detect_sequences(canon_all, spec, label="WARN->ERROR")
                sessions = correlate_start_end(canon_all, start_contains="Action start", end_contains="Action ended", correlate_key="msi_action")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Sequence Hits**")
                if chain_hits:
                    seq_rows = [{
                        "Label": h.label,
                        "Start": str(h.start),
                        "End": str(h.end),
                        "Span (s)": (h.end - h.start).total_seconds(),
                        "Len": len(h.indices),
                    } for h in chain_hits[:50]]
                    render_data_table(pd.DataFrame(seq_rows), "Sequences")
                else:
                    st.info("No sequence patterns matched.")
            
            with col2:
                st.markdown("**Sessions**")
                if sessions:
                    ses_rows = [{
                        "Key": s.key,
                        "Start": str(s.start),
                        "End": (str(s.end) if s.end else ""),
                        "Duration (s)": (s.duration_sec if s.duration_sec is not None else ""),
                        "Source": s.source,
                    } for s in sessions[:50]]
                    render_data_table(pd.DataFrame(ses_rows), "Sessions")
                else:
                    st.info("No start/end session pairs detected.")

    with tab_reports:
        st.session_state["current_step"] = 4
        st.subheader("[U+1F4C4] Generate Reports")
        
        render_info_card(
            "Report Contents",
            "- System info and metadata\n- Errors, timeline, and validations\n- RCA summary (optional AI)\n- Charts and insights",
            "[U+1F4CB]",
            "#e3f2fd"
        )

        # Report generation buttons
        report_actions = []
        
        if use_python_eng:
            report_actions.append({
                "key": "no_ai",
                "label": "[U+1F4C4] Standard Report",
                "type": "secondary"
            })
        
        if use_local_llm:
            report_actions.append({
                "key": "local_ai",
                "label": "[U+1F916] Local AI Report",
                "type": "primary"
            })
        
        if use_cloud_ai:
            report_actions.append({
                "key": "cloud_ai",
                "label": "[U+2601][U+FE0F] Cloud AI Report",
                "type": "primary"
            })

        selected_action = render_action_buttons(report_actions, "report")
        
        if selected_action == "no_ai":
            with st.spinner("Generating standard report..."):
                pdf = report.generate_pdf(redacted_events, redacted_metadata, st.session_state.get("validation_result", {}), {}, user_name=user_name, app_name=app_name, ai_summary=None, user_context=user_context)
                st.download_button("Download Standard Report", data=pdf, file_name="LogSense_Report_Standard.pdf", mime="application/pdf")
        
        elif selected_action == "local_ai":
            with st.spinner("Generating AI summary using Local LLM..."):
                ai_summary = ai_rca.analyze_with_ai(redacted_events, redacted_metadata, [], user_context, offline=True)
                pdf = report.generate_pdf(redacted_events, redacted_metadata, st.session_state.get("validation_result", {}), {}, user_name=user_name, app_name=app_name, ai_summary=ai_summary, user_context=user_context)
                st.download_button("Download Local AI Report", data=pdf, file_name="LogSense_Report_LocalAI.pdf", mime="application/pdf")
        
        elif selected_action == "cloud_ai":
            with st.spinner("Generating AI summary using OpenAI..."):
                ai_summary = ai_rca.analyze_with_ai(redacted_events, redacted_metadata, [], user_context, offline=False)
                pdf = report.generate_pdf(redacted_events, redacted_metadata, st.session_state.get("validation_result", {}), {}, user_name=user_name, app_name=app_name, ai_summary=ai_summary, user_context=user_context)
                st.download_button("Download Cloud AI Report", data=pdf, file_name="LogSense_Report_CloudAI.pdf", mime="application/pdf")

        # One-Pager PDF
        st.markdown("---")
        st.subheader("[U+1F4CB] Executive Summary (One-Pager)")
        if st.button("Generate Executive Summary", use_container_width=True):
            with st.spinner("Building executive summary..."):
                try:
                    canon_all = adapt_events_to_canonical(redacted_events)
                    meta_block = {
                        "build": build_number or app_version or "",
                        "platform": test_environment,
                        "versions": {"app": app_version},
                        "ts_range": f"{str(canon_all[0].ts) if canon_all and canon_all[0].ts else ''} .. {str(canon_all[-1].ts) if canon_all and canon_all[-1].ts else ''}",
                    }
                    evidence = [{
                        "ts": (str(ev.ts) if ev.ts else ""),
                        "source": ev.source,
                        "level": ev.level,
                        "event_id": ev.event_id,
                        "message": ev.message,
                    } for ev in canon_all[:250]]
                    payload = {
                        "meta": meta_block,
                        "deltas": {"new": [], "resolved": [], "persisting": []},
                        "observations": {"spikes": [], "gaps": [], "first_seen": [], "clock_anomalies": []},
                        "rca": {"root_causes": [], "next_actions": [], "confidence": 0.0},
                        "evidence": evidence,
                    }
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        out_path = build_onepager_pdf(payload, tmp.name, include_annexes=True)
                        with open(out_path, "rb") as f:
                            data = f.read()
                    st.download_button("Download Executive Summary", data=data, file_name="LogSense_Executive_Summary.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Failed to build executive summary: {e}")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 12px;'>"
    "LogSense Enterprise Log Analysis Platform | "
    f"Session: {st.session_state['session_id']} | "
    "Developed by Subodh Kc"
    "</div>", 
    unsafe_allow_html=True
)