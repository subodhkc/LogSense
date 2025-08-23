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
import hashlib

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
# Lazy load heavy ML modules to avoid memory issues at startup
clustering_model = None
decision_tree_model = None
anomaly_svm = None
from rca_rules import get_all_rca_summaries

# Advanced analytics - lazy load to avoid heavy ML imports at startup
AdvancedAnalyticsEngine = None

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
    page_icon="LOG",
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

# Cached helpers
@st.cache_data(show_spinner=False)
def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b or b"").hexdigest()

@st.cache_data(show_spinner=False)
def _parse_logs_cached(content: str, fname: str):
    return analysis.parse_logs(content, fname=fname)

# --- Welcome Screen ---
if "show_welcome" not in st.session_state:
    st.session_state["show_welcome"] = True

if st.session_state["show_welcome"]:
    render_welcome_screen()
    st.stop()

# --- Main Interface ---
render_header()
render_progress_indicator(st.session_state["current_step"])

with st.form("user_context_form"):
    # User Information Section
    with st.expander("User & Test Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            user_name = st.text_input("Your Name", key="user_name", placeholder="Enter your full name", help="This will appear in your final report.")
            app_name = st.text_input("Application Being Tested", key="app_name", placeholder="e.g., HP Power Manager", help="Used to focus log filtering and reporting.")
        with col2:
            app_version = st.text_input("Application Version", key="app_version", placeholder="e.g., v2.1.3 or Build 12345", help="Version of the application being tested")
            test_environment = st.selectbox("Test Environment", ["Production", "Staging", "Development", "QA", "Pre-production", "Other"], key="test_environment", help="Environment where testing occurred")

    # Issue Description Section
    with st.expander("Issue Description & Context", expanded=True):
        issue_description = st.text_area(
            "Describe the Issue", 
            key="issue_description",
            placeholder="What problem are you experiencing? Be specific about symptoms, error messages, and impact.",
            height=100,
            help="Detailed description helps AI provide better root cause analysis"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            deployment_method = st.selectbox("Deployment Method", ["DASH Imaging", "SoftPaq Installation", "Manual Install", "Group Policy", "SCCM", "Other"], key="deployment_method")
            build_changes = st.text_area("Recent Changes", key="build_changes", placeholder="Any recent updates, patches, or configuration changes", height=100)
        with col2:
            build_number = st.text_input("Build/Version Number", key="build_number", placeholder="e.g., 26000.1000")
            previous_version = st.text_input("Previous Working Version", key="previous_version", placeholder="Last known good version")

    # Additional information for reporting (collapsible)
    with st.expander("Additional Information (Optional)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            hw_model = st.text_input("Hardware Model", key="hw_model", placeholder="e.g., HP EliteBook 840 G10")
            os_build = st.text_input("OS Build", key="os_build", placeholder="e.g., Windows 11 26000.1000")
            region = st.text_input("Region/Locale", key="region", placeholder="e.g., US, EMEA")
            test_run_id = st.text_input("Test Run ID", key="test_run_id", placeholder="e.g., CI-12345 or Manual-2025-08-21")
        with col2:
            network_constraints = st.text_input("Network Constraints", key="network_constraints", placeholder="e.g., Proxy required, firewalled, offline")
            proxy_config = st.text_input("Proxy Config", key="proxy_config", placeholder="e.g., http://proxy:8080")
            device_sku = st.text_input("Device SKU", key="device_sku", placeholder="Optional device SKU or platform code")
            notes_private = st.text_area("Private Notes (not shared)", key="notes_private", height=80)

    submitted_controls = st.form_submit_button("Apply / Update")

# Gate the app until the user applies inputs at least once
if submitted_controls:
    st.session_state["controls_submitted"] = True
if not st.session_state.get("controls_submitted"):
    st.info("Configure inputs and click 'Apply / Update' to proceed.")
    st.stop()

# File Upload Section
with st.expander("Log File Upload", expanded=True):
    uploaded_file = st.file_uploader(
        "Upload Log Files (ZIP recommended)", 
        type=["zip", "txt", "log"], 
        help="Upload a ZIP file containing multiple logs, or individual log files."
    )

    # Initialize local variables from session for rendering
    events = st.session_state.get("events", [])
    redacted_events = st.session_state.get("redacted_events", [])
    redacted_metadata = st.session_state.get("redacted_metadata", {})

    if uploaded_file is not None:
        st.session_state["current_step"] = 1

        # Compute content hash to avoid reprocessing unchanged file(s)
        try:
            uploaded_bytes = uploaded_file.getvalue()
        except Exception:
            # Fallback if getvalue not available (ZIP streaming), read via buffer
            uploaded_bytes = uploaded_file.read()
        file_hash = _hash_bytes(uploaded_bytes)

        if st.session_state.get("uploaded_file_hash") != file_hash:
            with st.spinner("Processing uploaded files..."):
                events_new = []
                files_processed = 0
                if uploaded_file.name.endswith('.zip'):
                    with zipfile.ZipFile(io.BytesIO(uploaded_bytes), 'r') as zip_ref:
                        zip_contents = zip_ref.namelist()
                        log_files = [f for f in zip_contents if f.endswith(('.txt', '.log'))]

                        render_info_card(
                            "Archive Contents", 
                            f"Found {len(log_files)} log files in ZIP archive ({len(zip_contents)} total files)",
                            ""
                        )

                        for file_name in log_files:
                            with zip_ref.open(file_name) as file:
                                content = file.read().decode('utf-8', errors='ignore')
                                file_events = _parse_logs_cached(content, fname=file_name)
                                events_new.extend(file_events)
                        files_processed = len(log_files)
                else:
                    content = uploaded_bytes.decode('utf-8', errors='ignore')
                    events_new = _parse_logs_cached(content, fname=uploaded_file.name)
                    files_processed = 1

            st.session_state["events"] = events_new
            st.session_state["files_processed"] = files_processed
            st.session_state["events_analyzed"] = len(events_new)

            render_status_badge("success", f"Processed {len(events_new)} log events")

            # Apply redaction only when events change
            with st.spinner("Applying redaction patterns..."):
                red_evts, red_meta = redaction.apply_redaction(events_new, {})

            st.session_state["redacted_events"] = red_evts
            st.session_state["redacted_metadata"] = red_meta
            st.session_state["uploaded_file_hash"] = file_hash

            # Invalidate dependent artifacts
            for k in ("ai_summary_local", "ai_summary_cloud", "pdf_standard", "pdf_local_ai", "pdf_cloud_ai"):
                st.session_state.pop(k, None)

            redacted_events = red_evts
            redacted_metadata = red_meta
            events = events_new

            render_status_badge("success", f"Redaction complete. {len(red_evts)} events processed.")
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
        # Optional extras
        "hw_model": st.session_state.get("hw_model"),
        "os_build": st.session_state.get("os_build"),
        "region": st.session_state.get("region"),
        "test_run_id": st.session_state.get("test_run_id"),
        "network_constraints": st.session_state.get("network_constraints"),
        "proxy_config": st.session_state.get("proxy_config"),
        "device_sku": st.session_state.get("device_sku"),
        "notes_private": st.session_state.get("notes_private"),
    }

    # Test Plan Section
    if use_python_eng:
        with st.expander("Test Plan Validation", expanded=False):
            available_plans = setup.get_available_test_plans()
            if available_plans:
                # Friendly mapping for known plans (SoftPaq vs Factory Image/Pulsar)
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
                    # Extract filename from selection
                    try:
                        selected_plan_file = sel.split(" - ", 1)[1]
                    except Exception:
                        selected_plan_file = sel
                    plan_data = setup.get_test_plan(selected_plan_file)
                    if plan_data:
                        friendly_name = plan_labels.get(selected_plan_file, selected_plan_file)
                        rich_result = test_plan.validate_plan(plan_data, events, plan_name=friendly_name)
                        st.session_state["validation_result"] = rich_result
                        # Render compact table view
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
                            # Summary chips
                            summ = rich_result.get("summary", {})
                            render_status_badge(
                                "info",
                                f"Pass: {summ.get('pass_count',0)} | Fail: {summ.get('fail_count',0)}" + (
                                    f" | First failure phase: {summ.get('first_failure_phase')}" if summ.get('first_failure_phase') else ""
                                ),
                            )
                        else:
                            st.info("No test plan results available.")
                    else:
                        st.error("Failed to load selected test plan.")
            else:
                st.info("No test plans available in the plans/ directory.")

    # Timeline and Issues
    st.subheader("Timeline & Issues Analysis")
    
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
        render_info_card("No Issues Found", "No warnings or errors detected in the logs.", "", "#d4edda")

    # Tabs for advanced analysis
    tab_templates, tab_ml, tab_corr, tab_reports = st.tabs(["Templates", "ML Insights", "Correlations", "Reports"])

    with tab_templates:
        if st.checkbox(
            "Show Templates (Structural Patterns)",
            value=False,
            help="Extracts normalized message templates (e.g., masking IDs, IPs, counters) to reveal recurring log patterns. Use high-count templates to identify noisy components or common failure shapes."
        ):
            st.subheader("Templates (Structural Patterns)")
            render_info_card(
                "How to use",
                "High-frequency templates point to dominant behaviors or repeated errors. Compare top templates before/after a change, or filter by severity to isolate failure patterns.",
                "",
                "#f8f9fa"
            )
            with st.spinner("Mining templates..."):
                canon_all = adapt_events_to_canonical(redacted_events)
                tmpl = TemplateExtractor()
                assigned = tmpl.assign(canon_all)
                summary_rows = tmpl.summary()
            if summary_rows:
                tmpl_df = pd.DataFrame([{ "Template ID": tid, "Count": cnt, "Template": tpl } for tid, cnt, tpl in summary_rows])
                render_data_table(tmpl_df, "Template Analysis")

    with tab_ml:
        st.subheader("Machine Learning Insights")
        render_info_card(
            "ML Analysis",
            "Use machine learning to uncover hidden patterns: clustering, anomaly detection, and severity prediction.",
            ""
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "Run Clustering",
                use_container_width=True,
                help="Groups similar events by message structure/features. Use clusters to spot families of related errors and reduce noise."
            ):
                with st.spinner("Clustering events..."):
                    if clustering_model is None:
                        import clustering_model as _clustering_model
                        clustering_model = _clustering_model
                    cluster_fig = clustering_model.cluster_events(events)
                    if cluster_fig:
                        st.pyplot(cluster_fig)

        with col2:
            if st.button(
                "Severity Prediction",
                use_container_width=True,
                help="Estimates severity trends from features. Use it to prioritize attention across components or time windows."
            ):
                with st.spinner("Analyzing severity predictions..."):
                    if decision_tree_model is None:
                        import decision_tree_model as _decision_tree_model
                        decision_tree_model = _decision_tree_model
                    severity_fig = decision_tree_model.analyze_event_severity(events)
                    if severity_fig:
                        st.pyplot(severity_fig)

        with col3:
            if st.button(
                "Anomaly Detection",
                use_container_width=True,
                help="Flags events/time windows that deviate from baseline. Use anomalies to investigate spikes or rare failure sequences."
            ):
                with st.spinner("Detecting anomalies..."):
                    if anomaly_svm is None:
                        import anomaly_svm as _anomaly_svm
                        anomaly_svm = _anomaly_svm
                    anomaly_fig = anomaly_svm.detect_anomalies(events)
                    if anomaly_fig:
                        st.pyplot(anomaly_fig)

    with tab_corr:
        if st.checkbox(
            "Show Correlations (Sequences & Sessions)",
            value=False,
            help="Finds WARN->ERROR sequences within a time window and pairs 'start'/'ended' actions into sessions. Use sequence hits to locate causal chains, and sessions to measure operation durations."
        ):
            st.subheader("Correlations")
            render_info_card(
                "How to use",
                "Sequence hits suggest causal chains (e.g., warnings escalating to errors). Sessions help quantify operation durations and incomplete runs. Focus on long or unfinished sessions.",
                "",
                "#f8f9fa"
            )
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
        st.subheader("Generate Reports")
        
        render_info_card(
            "Report Contents",
            "- System info and metadata\n- Errors, timeline, and validations\n- RCA summary (optional AI)\n- Charts and insights",
            "",
            "#e3f2fd"
        )

        # Report generation buttons
        report_actions = []
        
        if use_python_eng:
            report_actions.append({
                "key": "no_ai",
                "label": "Standard Report",
                "type": "secondary"
            })
        
        if use_local_llm:
            report_actions.append({
                "key": "local_ai",
                "label": "Local AI Report",
                "type": "primary"
            })
        
        if use_cloud_ai:
            report_actions.append({
                "key": "cloud_ai",
                "label": "Cloud AI Report",
                "type": "primary"
            })

        selected_action = render_action_buttons(report_actions, "report")
        if selected_action:
            st.session_state["active_report_mode"] = selected_action

        # Build analytical insights for Standard Report with Advanced Analytics
        def _build_python_insights(evts):
            recs = []
            try:
                # Lazy load advanced analytics engine
                global AdvancedAnalyticsEngine
                if AdvancedAnalyticsEngine is None:
                    import sys
                    import os
                    sys.path.append(os.path.join(os.path.dirname(__file__), 'Python Modules'))
                    from analyzer.advanced_analytics import AdvancedAnalyticsEngine as _AdvancedAnalyticsEngine
                    AdvancedAnalyticsEngine = _AdvancedAnalyticsEngine
                
                # Initialize advanced analytics engine
                analytics_engine = AdvancedAnalyticsEngine()
                
                # Run comprehensive analysis
                advanced_results = analytics_engine.run_comprehensive_analysis(evts)
                
                # Basic KPIs
                total = len(evts)
                errs = [e for e in evts if getattr(e, "severity", "").upper() in ("ERROR", "CRITICAL")]
                warns = [e for e in evts if getattr(e, "severity", "").upper() == "WARNING"]
                recs.append({"severity": "INFO", "message": f"Total events: {total}"})
                recs.append({"severity": "INFO", "message": f"Errors/Critical: {len(errs)} | Warnings: {len(warns)}"})

                # Advanced Analytics Results
                if 'key_insights' in advanced_results:
                    for insight in advanced_results['key_insights'][:3]:
                        recs.append({"severity": "INFO", "message": f"Advanced Analysis: {insight}"})

                # Error Spikes Detection
                if advanced_results.get('error_spikes'):
                    spike_count = len(advanced_results['error_spikes'])
                    high_spikes = [s for s in advanced_results['error_spikes'] if s.get('severity') == 'HIGH']
                    if high_spikes:
                        recs.append({
                            "severity": "CRITICAL", 
                            "message": f"Detected {len(high_spikes)} critical error spikes - system instability periods identified"
                        })
                    elif spike_count > 0:
                        recs.append({
                            "severity": "WARNING", 
                            "message": f"Detected {spike_count} error spikes - monitor for recurring patterns"
                        })

                # Root Cause Ranking
                if advanced_results.get('root_cause_ranking'):
                    top_cause = advanced_results['root_cause_ranking'][0]
                    confidence = top_cause.get('root_cause_score', 0)
                    if confidence > 0.7:
                        recs.append({
                            "severity": "CRITICAL",
                            "message": f"Primary root cause: {top_cause['component']} (confidence: {confidence:.2f}) - {top_cause['error_count']} errors"
                        })
                    elif confidence > 0.4:
                        recs.append({
                            "severity": "WARNING",
                            "message": f"Likely root cause: {top_cause['component']} (confidence: {confidence:.2f}) - requires investigation"
                        })

                # Component Correlations
                if advanced_results.get('component_correlations'):
                    high_corr = [c for c in advanced_results['component_correlations'] if c.get('strength') == 'HIGH']
                    if high_corr:
                        corr = high_corr[0]
                        recs.append({
                            "severity": "WARNING",
                            "message": f"Strong correlation detected: {corr['component1']} [U+2194] {corr['component2']} (score: {corr['correlation_score']:.2f})"
                        })

                # Entropy Analysis
                if advanced_results.get('entropy_analysis', {}).get('component_entropy'):
                    entropy = advanced_results['entropy_analysis']['component_entropy']
                    diversity = advanced_results['entropy_analysis'].get('component_diversity', 0)
                    if entropy > 3.0:
                        recs.append({
                            "severity": "INFO",
                            "message": f"High error diversity detected across {diversity} components (entropy: {entropy:.2f}) - widespread issues"
                        })
                    elif entropy < 1.0:
                        recs.append({
                            "severity": "WARNING",
                            "message": f"Low error diversity (entropy: {entropy:.2f}) - concentrated failure pattern in few components"
                        })

                # Fallback to basic analysis if advanced fails
                if not any('Advanced Analysis:' in r.get('message', '') for r in recs):
                    # Top error components (fallback)
                    from collections import Counter
                    top_comps = Counter([getattr(e, "component", "") for e in errs]).most_common(3)
                    if top_comps:
                        recs.append({
                            "severity": "INFO",
                            "message": "Top error-prone components: " + ", ".join([f"{c} ({n})" for c, n in top_comps if c])
                        })

                    # Most frequent ERROR message (fallback)
                    msg_counts = Counter([getattr(e, "message", "").strip()[:120] for e in errs if getattr(e, "message", "")]).most_common(1)
                    if msg_counts:
                        recs.append({
                            "severity": "WARNING",
                            "message": f"Most frequent error: '{msg_counts[0][0]}' ({msg_counts[0][1]} occurrences)"
                        })

                # Time range analysis
                try:
                    ts_sorted = sorted([e.timestamp for e in evts if getattr(e, "timestamp", None)])
                    if ts_sorted:
                        start, end = ts_sorted[0], ts_sorted[-1]
                        recs.append({"severity": "INFO", "message": f"Time range: {start} .. {end}"})
                    hour_counts = Counter([getattr(e.timestamp, 'hour', None) for e in errs if getattr(e, 'timestamp', None) is not None])
                    if hour_counts:
                        peak_hour, peak_cnt = max(hour_counts.items(), key=lambda x: x[1])
                        recs.append({"severity": "WARNING", "message": f"Error spike around {peak_hour:02d}:00 ({peak_cnt} events)"})
                except Exception:
                    pass

                # RCA rule summaries
                try:
                    rca_list = get_all_rca_summaries(evts)
                    for item in (rca_list or [])[:3]:  # Reduced to 3 to make room for advanced analytics
                        if isinstance(item, dict):
                            msg = item.get("message") or item.get("summary") or str(item)
                            sev = item.get("severity", "INFO")
                        else:
                            msg, sev = str(item), "INFO"
                        recs.append({"severity": sev, "message": f"RCA: {msg}"})
                except Exception:
                    pass
                    
            except Exception as e:
                # Fallback to basic analysis if advanced analytics fails
                recs.append({"severity": "ERROR", "message": f"Advanced analytics unavailable: {str(e)}"})
                
            return recs

        if selected_action == "no_ai":
            with st.spinner("Generating standard report..."):
                py_insights = _build_python_insights(redacted_events)
                pdf = report.generate_pdf(
                    redacted_events,
                    redacted_metadata,
                    st.session_state.get("validation_result", {}),
                    py_insights,
                    user_name=user_name,
                    app_name=app_name,
                    ai_summary=None,
                    user_context=user_context,
                )
                st.session_state["pdf_standard"] = pdf
        
        elif selected_action == "local_ai":
            with st.spinner("Generating AI summary using Local LLM..."):
                ai_summary = ai_rca.analyze_with_ai(redacted_events, redacted_metadata, [], user_context, offline=True)
                st.session_state["ai_summary_local"] = ai_summary
                pdf = report.generate_pdf(redacted_events, redacted_metadata, st.session_state.get("validation_result", {}), {}, user_name=user_name, app_name=app_name, ai_summary=ai_summary, user_context=user_context)
                st.session_state["pdf_local_ai"] = pdf
            st.session_state["active_report_mode"] = "local_ai"

        elif selected_action == "cloud_ai":
            with st.spinner("Generating AI summary using OpenAI..."):
                ai_summary = ai_rca.analyze_with_ai(redacted_events, redacted_metadata, [], user_context, offline=False)
                st.session_state["ai_summary_cloud"] = ai_summary
                pdf = report.generate_pdf(redacted_events, redacted_metadata, st.session_state.get("validation_result", {}), {}, user_name=user_name, app_name=app_name, ai_summary=ai_summary, user_context=user_context)
                st.session_state["pdf_cloud_ai"] = pdf
            st.session_state["active_report_mode"] = "cloud_ai"

        # Always show download buttons for generated reports
        st.markdown("---")
        st.subheader("Download Reports")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if "pdf_standard" in st.session_state:
                st.download_button(
                    "Standard Report", 
                    data=st.session_state["pdf_standard"], 
                    file_name="LogSense_Report_Standard.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )
        
        with col2:
            if "pdf_local_ai" in st.session_state:
                st.download_button(
                    "Local AI Report", 
                    data=st.session_state["pdf_local_ai"], 
                    file_name="LogSense_Report_LocalAI.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )
        
        with col3:
            if "pdf_cloud_ai" in st.session_state:
                st.download_button(
                    "Cloud AI Report", 
                    data=st.session_state["pdf_cloud_ai"], 
                    file_name="LogSense_Report_CloudAI.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )

        # Persistent Chat Panels (render based on session state)
        active_mode = st.session_state.get("active_report_mode")
        if active_mode in ("local_ai", "cloud_ai"):
            st.markdown("---")
            st.subheader("Chat with AI about this report")
            chat_key = "chat_local_ai" if active_mode == "local_ai" else "chat_cloud_ai"
            if chat_key not in st.session_state:
                st.session_state[chat_key] = []
            # Show prior messages
            for role, msg in st.session_state[chat_key]:
                with st.chat_message(role):
                    st.markdown(msg)
            # Chat input
            prompt = st.chat_input("Ask a question about the findings, errors, or next steps...")
            if prompt:
                st.session_state[chat_key].append(("user", prompt))
                with st.spinner("Thinking..." if active_mode == "local_ai" else "Consulting OpenAI..."):
                    # Create contextual chat prompt based on user question and report
                    ai_summary = st.session_state.get("ai_summary_local") if active_mode == "local_ai" else st.session_state.get("ai_summary_cloud")
                    
                    # Build contextual chat prompt
                    chat_context = {
                        "user_question": prompt,
                        "previous_analysis": ai_summary or "No previous analysis available",
                        "chat_mode": True
                    }
                    
                    # Add relevant log snippets based on user question keywords
                    relevant_events = []
                    question_lower = prompt.lower()
                    keywords = ["error", "warning", "fail", "critical", "timeout", "crash", "exception"]
                    
                    try:
                        if any(kw in question_lower for kw in keywords):
                            # Include recent errors/warnings relevant to the question
                            for ev in redacted_events[-50:]:  # Last 50 events for context
                                ev_message = getattr(ev, 'message', '')
                                ev_component = getattr(ev, 'component', '')
                                if any(kw in ev_message.lower() or kw in ev_component.lower() 
                                       for kw in question_lower.split() if len(kw) > 3):
                                    relevant_events.append(ev)
                        
                        if not relevant_events:
                            # Fallback: include recent critical/error events
                            relevant_events = [ev for ev in redacted_events 
                                             if getattr(ev, 'severity', '').upper() in ('ERROR', 'CRITICAL')][-10:]
                    except Exception:
                        # Ultimate fallback: use last 10 events
                        relevant_events = redacted_events[-10:] if redacted_events else []
                    
                    try:
                        reply = ai_rca.analyze_with_ai(
                            relevant_events,
                            redacted_metadata,
                            [],
                            chat_context,
                            offline=(active_mode == "local_ai")
                        )
                    except Exception as e:
                        # Safe fallback reply to avoid cascading UI failure
                        prior = (ai_summary or "N/A")
                        reply = (
                            "I ran into an issue while generating a detailed answer, but here is a concise response based on the available context.\n\n"
                            f"Previous analysis summary:\n{prior}\n\n"
                            "Next steps:\n"
                            "- Re-check recent ERROR/CRITICAL events around the time of the issue.\n"
                            "- Validate installation phases (download, extraction, signature, apply, reboot).\n"
                            "- If this persists, please try narrowing the timeframe or keywords and ask again."
                        )
                st.session_state[chat_key].append(("assistant", reply))
                with st.chat_message("assistant"):
                    st.markdown(reply)

        # One-Pager PDF
        st.markdown("---")
        st.subheader("Executive Summary (One-Pager)")
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