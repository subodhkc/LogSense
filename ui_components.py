# ui_components.py - Corporate UI components for LogSense

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

def render_header():
    """Render professional header with branding and navigation."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown("### 🔍 LogSense")
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 10px;'>
            <h4 style='color: #1f77b4; margin: 0;'>Enterprise Log Analysis Platform</h4>
            <p style='color: #666; margin: 0; font-size: 14px;'>Intelligent diagnostics for system provisioning and deployment</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style='text-align: right; font-size: 12px; color: #888;'>
            Session: {st.session_state.get('session_id', 'New')}
        </div>
        """, unsafe_allow_html=True)

def render_progress_indicator(current_step: int, total_steps: int = 5):
    """Render progress indicator for multi-step workflow using Streamlit columns.

    Avoids relying on a single large HTML block which can sometimes be rendered
    as literal text in certain Streamlit configurations.
    """
    steps = ["Upload", "Configure", "Analyze", "Review", "Export"]

    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        if i < current_step:
            color = "#28a745"  # Green for completed
            icon = "✓"
        elif i == current_step:
            color = "#1f77b4"  # Blue for current
            icon = "●"
        else:
            color = "#dee2e6"  # Gray for pending
            icon = "○"

        with col:
            st.markdown(
                f"<div style='text-align: center; color: {color}; font-size: 20px;'>{icon}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='text-align: center; color: {color}; font-size: 12px; margin-top: 5px;'>{step}</div>",
                unsafe_allow_html=True,
            )

def render_info_card(title: str, content: str, icon: str = "ℹ️", color: str = "#e3f2fd"):
    """Render information card with professional styling."""
    st.markdown(f"""
    <div style='
        background-color: {color};
        border-left: 4px solid #1f77b4;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    '>
        <h4 style='margin: 0 0 10px 0; color: #1f77b4;'>{icon} {title}</h4>
        <p style='margin: 0; color: #333;'>{content}</p>
    </div>
    """, unsafe_allow_html=True)

def render_metric_cards(metrics: Dict[str, Any]):
    """Render key metrics in card format."""
    cols = st.columns(len(metrics))
    
    for i, (key, value) in enumerate(metrics.items()):
        with cols[i]:
            st.markdown(f"""
            <div style='
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            '>
                <h3 style='color: #1f77b4; margin: 0;'>{value}</h3>
                <p style='color: #666; margin: 5px 0 0 0; font-size: 14px;'>{key}</p>
            </div>
            """, unsafe_allow_html=True)

def render_status_badge(status: str, message: str = ""):
    """Render status badge with appropriate styling."""
    colors = {
        "success": "#28a745",
        "warning": "#ffc107", 
        "error": "#dc3545",
        "info": "#17a2b8",
        "processing": "#6f42c1"
    }
    
    color = colors.get(status.lower(), "#6c757d")
    
    st.markdown(f"""
    <span style='
        background-color: {color};
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 10px;
    '>{status.upper()}</span>
    <span style='color: #666; font-size: 14px;'>{message}</span>
    """, unsafe_allow_html=True)

def render_data_table(df: pd.DataFrame, title: str, max_height: int = 400):
    """Render data table with professional styling and controls."""
    if df.empty:
        st.info(f"No {title.lower()} data available")
        return
    
    st.markdown(f"#### {title}")
    
    # Add search and filter controls
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input(f"Search {title}", key=f"search_{title}")
    with col2:
        show_all = st.checkbox(f"Show all {len(df)} rows", key=f"show_all_{title}")
    
    # Apply search filter
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        df = df[mask]
    
    # Display table with styling
    if not show_all and len(df) > 20:
        df = df.head(20)
        st.caption(f"Showing first 20 of {len(df)} rows. Check 'Show all' to see more.")
    
    st.dataframe(
        df,
        use_container_width=True,
        height=min(max_height, len(df) * 35 + 50)
    )

def render_action_buttons(actions: List[Dict[str, Any]], key_prefix: str = ""):
    """Render action buttons with consistent styling."""
    cols = st.columns(len(actions))
    
    for i, action in enumerate(actions):
        with cols[i]:
            button_type = action.get('type', 'primary')
            disabled = action.get('disabled', False)
            
            if button_type == 'primary':
                clicked = st.button(
                    action['label'], 
                    key=f"{key_prefix}_{action['key']}", 
                    disabled=disabled,
                    type='primary'
                )
            else:
                clicked = st.button(
                    action['label'], 
                    key=f"{key_prefix}_{action['key']}", 
                    disabled=disabled
                )
            
            if clicked and not disabled:
                return action['key']
    
    return None

def render_sidebar_config():
    """Render enhanced sidebar configuration."""
    st.sidebar.markdown("---")
    
    # Engine Configuration
    with st.sidebar.expander("Engine Configuration", expanded=True):
        engines = {
            "python": st.checkbox("Python Analytics", value=True, help="Rule-based analysis and pattern detection"),
            "local_llm": st.checkbox("Local AI (Phi-2)", value=True, help="Offline AI analysis using Microsoft Phi-2"),
            "cloud_ai": st.checkbox("Cloud AI (OpenAI)", value=False, help="Enhanced AI analysis via OpenAI API")
        }
    
    # Analysis Settings
    with st.sidebar.expander("Analysis Settings"):
        settings = {
            "include_charts": st.checkbox("Include Charts", value=True),
            "detailed_timeline": st.checkbox("Detailed Timeline", value=False),
            "advanced_correlations": st.checkbox("Advanced Correlations", value=False),
            "export_raw_data": st.checkbox("Export Raw Data", value=False)
        }
    
    # Session Info
    with st.sidebar.expander("Session Info"):
        st.metric("Files Processed", st.session_state.get('files_processed', 0))
        st.metric("Events Analyzed", st.session_state.get('events_analyzed', 0))
        st.metric("Issues Found", st.session_state.get('issues_found', 0))
    
    return engines, settings

def render_welcome_screen():
    """Render enhanced welcome screen with better onboarding."""
    st.markdown("""
    <div style='text-align: center; padding: 40px 20px;'>
        <h1 style='color: #1f77b4; margin-bottom: 20px;'>LogSense</h1>
        <h3 style='color: #666; font-weight: normal; margin-bottom: 30px;'>
            Enterprise Log Analysis Platform
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature highlights
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h4 style='color: #1f77b4;'>Intelligent Analysis</h4>
            <p style='color: #666;'>AI-powered root cause analysis with pattern recognition and anomaly detection.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h4 style='color: #1f77b4;'>Privacy First</h4>
            <p style='color: #666;'>All analysis happens locally. Your data never leaves your environment.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h4 style='color: #1f77b4;'>Rich Insights</h4>
            <p style='color: #666;'>Interactive dashboards, timeline analysis, and comprehensive reporting.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick start section
    st.markdown("---")
    st.markdown("### Quick Start")
    
    render_info_card(
        "Getting Started",
        "Upload your log files (ZIP format recommended), configure your analysis preferences, and let LogSense identify issues and provide actionable insights.",
        "",
        "#f8f9fa"
    )
    
    # Start button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Start Analysis", type="primary", use_container_width=True):
            st.session_state["show_welcome"] = False
            st.rerun()
