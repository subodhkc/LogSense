import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
from io import BytesIO
from charts import (
    plot_severity_distribution,
    plot_top_error_components,
    plot_event_frequency_by_hour
)

def sanitize(text):
    """Ensure string is safely encodable in Latin-1"""
    return str(text).replace('\ufeff', '').encode('latin-1', errors='replace').decode('latin-1')

def add_chart_image(pdf, fig, title):
    """Save a matplotlib figure to memory and embed in PDF"""
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, sanitize(title), ln=True)
    pdf.image(buf, x=10, y=25, w=180)
    plt.close(fig)

def generate_pdf(events, metadata, test_results, recommendations, user_name, app_name, ai_summary=None, user_context=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title & Metadata
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, sanitize("LogSense Report"), ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, sanitize(f"Generated for: {user_name}"), ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, sanitize(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
    pdf.cell(0, 8, sanitize(f"Application: {app_name}"), ln=True)
    
    # Add user context to report header
    if user_context:
        if user_context.get('app_version'):
            pdf.cell(0, 8, sanitize(f"Version: {user_context['app_version']}"), ln=True)
        if user_context.get('test_environment'):
            pdf.cell(0, 8, sanitize(f"Environment: {user_context['test_environment']}"), ln=True)
        if user_context.get('deployment_method'):
            pdf.cell(0, 8, sanitize(f"Deployment: {user_context['deployment_method']}"), ln=True)
        if user_context.get('issue_severity'):
            pdf.cell(0, 8, sanitize(f"Issue Severity: {user_context['issue_severity']}"), ln=True)
    pdf.ln(5)

    # System Metadata
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, sanitize("System Metadata:"), ln=True)
    pdf.set_font("Arial", '', 10)
    for key, value in metadata.items():
        pdf.cell(0, 8, sanitize(f"{key}: {value}"), ln=True)
    pdf.ln(5)

    # Timeline (Condensed to Errors Only, Max 5)
    error_events = [ev for ev in events if ev.severity in ["ERROR", "CRITICAL"]]
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, sanitize("Key Events Timeline (Top 5 ERROR/CRITICAL):"), ln=True)
    pdf.set_font("Arial", '', 10)
    if error_events:
        for ev in error_events[:5]:
            line = f"[{ev.timestamp}] {ev.component} - {ev.severity}: {ev.message}"
            pdf.cell(0, 8, sanitize(line), ln=True)
    else:
        pdf.cell(0, 8, sanitize("No ERROR or CRITICAL events found."), ln=True)
    pdf.ln(5)

    # Test Plan
    if test_results:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, sanitize("Test Plan Validation:"), ln=True)
        pdf.set_font("Arial", '', 10)
        for result in test_results:
            step = result.get("Step", "")
            status = result.get("Status", "")
            actual = result.get("Actual Result", "")
            line = f"Step: {step} - Status: {status} - Observed: {actual}"
            pdf.cell(0, 8, sanitize(line), ln=True)
        pdf.ln(5)

    # User Context Section
    if user_context and (user_context.get('issue_description') or user_context.get('build_changes')):
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, sanitize("Issue Context:"), ln=True)
        pdf.set_font("Arial", '', 10)
        if user_context.get('issue_description'):
            pdf.multi_cell(0, 8, sanitize(f"Issue Description: {user_context['issue_description']}"))
        if user_context.get('build_changes'):
            pdf.multi_cell(0, 8, sanitize(f"Recent Changes: {user_context['build_changes']}"))
        if user_context.get('reproduction_steps'):
            pdf.multi_cell(0, 8, sanitize(f"Reproduction Steps: {user_context['reproduction_steps']}"))
        pdf.ln(5)

    # Recommendations
    if recommendations:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, sanitize("Recommendations:"), ln=True)
        pdf.set_font("Arial", '', 10)
        
        # Handle both old and new recommendation formats
        rec_list = recommendations
        if isinstance(recommendations, dict) and recommendations.get('recommendations'):
            rec_list = recommendations['recommendations']
            pdf.cell(0, 8, sanitize(f"Analysis Summary: {recommendations.get('rules_fired', 0)} rules fired"), ln=True)
            pdf.ln(2)
        
        for rec in rec_list:
            if isinstance(rec, dict):
                severity = rec.get("severity", "INFO")
                message = rec.get("message", "")
                category = rec.get("category", "N/A")
                action = rec.get("action", "")
                line = f"- {severity}: {message} [Category: {category}]"
                if action:
                    line += f"\n  Action: {action}"
            else:
                line = f"- {rec}"
            pdf.multi_cell(0, 8, sanitize(line))
            pdf.ln(2)
        pdf.ln(3)

    # AI Summary
    if ai_summary:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, sanitize("Root Cause Summary:"), ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, sanitize(ai_summary))
        pdf.ln(5)

    # Charts
    try:
        add_chart_image(pdf, plot_severity_distribution(events), "Log Severity Distribution")
        top_err_fig = plot_top_error_components(events)
        if top_err_fig:
            add_chart_image(pdf, top_err_fig, "Top Error-Prone Components")
        add_chart_image(pdf, plot_event_frequency_by_hour(events), "Event Frequency by Hour of Day")
    except Exception as e:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Chart Rendering Error", ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, sanitize(str(e)))

    # Footer
    pdf.set_font("Arial", 'I', 9)
    pdf.set_y(-15)
    pdf.cell(0, 10, sanitize("Open Source Model Developed by Subodh Kc"), 0, 0, 'R')

    try:
        return pdf.output(dest='S').encode('latin1')
    except UnicodeEncodeError:
        return pdf.output(dest='S').encode('utf-8', errors='replace')

def generate_text_summary(events, metadata, test_results, recommendations):
    lines = []

    lines.append("=== System Metadata ===")
    for key, value in metadata.items():
        lines.append(f"{key}: {value}")

    error_events = [ev for ev in events if ev.severity in ["ERROR", "CRITICAL"]]
    lines.append("\n=== Key Events (Top 5 ERROR/CRITICAL only) ===")
    for ev in error_events[:5]:
        lines.append(f"[{ev.timestamp}] {ev.component} - {ev.severity}: {ev.message}")
    if not error_events:
        lines.append("No critical issues detected.")

    if test_results:
        lines.append("\n=== Test Plan Validation ===")
        for result in test_results:
            step = result.get("Step", "")
            status = result.get("Status", "")
            actual = result.get("Actual Result", "")
            lines.append(f"Step: {step} - Status: {status} - Observed: {actual}")

    if recommendations:
        lines.append("\n=== Recommendations ===")
        for rec in recommendations:
            if isinstance(rec, dict):
                severity = rec.get("severity", "INFO")
                message = rec.get("message", "")
                step = rec.get("step", "N/A")
                category = rec.get("category", "N/A")
                lines.append(f"- {severity}: {message} [Step: {step}, Category: {category}]")
            else:
                lines.append(f"- {rec}")

    return "\n".join(lines)
