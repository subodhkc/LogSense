# ai_rca.py - Hybrid AI RCA using offline LLM and OpenAI fallback

from openai import OpenAI
import traceback
import logging
import os
import time
from dotenv import load_dotenv
# Lazy import heavy offline model only when needed to avoid torch DLL load at startup
phi2_summarize = None  # will be set on-demand

# ----- Load .env and API key -----
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))

# ----- Internal Setup -----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_RCA")

MODEL_BACKEND = os.getenv("MODEL_BACKEND", "phi2").lower()  # phi2|legacy
if MODEL_BACKEND not in ("phi2", "legacy"):
    MODEL_BACKEND = "phi2"
if not os.getenv("CUDA_VISIBLE_DEVICES") and not os.getenv("FORCE_CPU"):
    logger.info("GPU not explicitly set; Phi-2 will use CPU if CUDA not available.")

# ----- Helper Functions -----
def format_logs_for_ai(events, metadata=None, test_results=None, context=None):
    lines = []
    
    # Add user context first for better AI understanding
    if context:
        lines.append("=== USER CONTEXT & ISSUE DESCRIPTION ===")
        if context.get("issue_description"):
            lines.append(f"Issue Description: {context['issue_description']}")
        if context.get("app_name") and context.get("app_version"):
            lines.append(f"Application: {context['app_name']} v{context['app_version']}")
        if context.get("deployment_method"):
            lines.append(f"Deployment Method: {context['deployment_method']}")
        if context.get("test_environment"):
            lines.append(f"Environment: {context['test_environment']}")
        if context.get("issue_severity"):
            lines.append(f"Severity: {context['issue_severity']}")
        if context.get("issue_frequency"):
            lines.append(f"Frequency: {context['issue_frequency']}")
        if context.get("build_changes"):
            lines.append(f"Recent Changes: {context['build_changes']}")
        if context.get("expected_behavior"):
            lines.append(f"Expected Behavior: {context['expected_behavior']}")
        if context.get("reproduction_steps"):
            lines.append(f"Reproduction Steps: {context['reproduction_steps']}")
        if context.get("additional_context"):
            lines.append(f"Additional Context: {context['additional_context']}")
        lines.append("")
    
    if metadata:
        lines.append("=== SYSTEM METADATA ===")
        for k, v in metadata.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    if test_results:
        lines.append("=== TEST PLAN RESULTS ===")
        for result in test_results:
            step = result.get("Step", "")
            status = result.get("Status", "")
            action = result.get("Step Action", "")
            lines.append(f"- Step {step}: {status} - {action}")
        lines.append("")

    lines.append("=== ERROR & CRITICAL EVENTS ===")
    filtered = [ev for ev in events if ev.severity in ("ERROR", "CRITICAL")]
    for ev in filtered:
        ts = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ev.timestamp, "strftime") else str(ev.timestamp)
        lines.append(f"[{ts}] [{ev.severity}] [{ev.component}] {ev.message}")

    return "\n".join(lines)

def analyze_with_ai(events, metadata=None, test_results=None, context=None, offline=True):
    """
    Quick fix: Skip offline analysis in Modal deployment to prevent hanging
    """
    # Force cloud AI in Modal deployment to prevent hanging
    if offline:
        offline = False
        print("[AI_RCA] Forcing cloud AI mode to prevent hanging on missing dependencies")
    # Check if this is a chat mode interaction
    is_chat_mode = context and context.get("chat_mode", False)
    
    if is_chat_mode:
        # Chat mode: respond to specific user question with context
        user_question = context.get("user_question", "")
        previous_analysis = context.get("previous_analysis", "")
        
        prompt = (
            "You are an expert log analysis assistant helping with follow-up questions about a previous RCA report.\n"
            f"**PREVIOUS ANALYSIS:**\n{previous_analysis}\n\n"
            f"**USER QUESTION:** {user_question}\n\n"
            "**INSTRUCTIONS:**\n"
            "- Answer the user's specific question based on the previous analysis and relevant log events\n"
            "- Be concise and directly address their concern\n"
            "- Reference specific log events or findings when relevant\n"
            "- If asking about next steps, provide actionable recommendations\n"
            "- If asking about specific errors, explain the technical details and impact\n"
            "- Keep responses focused and practical\n\n"
        )
    else:
        # Original RCA mode
        context_info = ""
        if context and context.get("issue_description"):
            context_info = f"\n\n**USER REPORTED ISSUE:** {context['issue_description']}\n"
            if context.get("expected_behavior"):
                context_info += f"**EXPECTED BEHAVIOR:** {context['expected_behavior']}\n"
            if context.get("reproduction_steps"):
                context_info += f"**REPRODUCTION STEPS:** {context['reproduction_steps']}\n"
            if context.get("build_changes"):
                context_info += f"**RECENT CHANGES:** {context['build_changes']}\n"
        
        formatted_logs = format_logs_for_ai(events, metadata, test_results, context)
        
        prompt = (
            "You are a senior QA automation engineer and SME on LOG analysis and expert in log diagnostics.\n"
            "You are reviewing system provisioning or installation logs from BIOS updates, firmware flashing, OS imaging, or agent deployments.\n"
            f"{context_info}\n"
            "Your task is to analyze the logs and produce a structured root cause analysis (RCA) report for technical stakeholders.\n"
            "Be concise, evidence-driven, and focus on the user's specific issue. Correlate log events with the reported problem.\n\n"
            "Respond in markdown format with the following sections:\n\n"
            "1. **Issue Correlation**  \n"
            "How do the log events correlate with the user's reported issue? What patterns match their description?\n\n"
            "2. **Log Overview**  \n"
            "Summarize the system operations observed in the logs — including install attempts, reboots, service changes, etc.\n\n"
            "3. **Key Events (ERROR/CRITICAL)**  \n"
            "List the most critical errors and their potential impact.\n\n"
            f"=== LOG DATA ===\n{formatted_logs}\n\nAnalysis:"
        )

    # Try offline AI first if requested
    if offline:
        try:
            # Quick dependency check before attempting model loading
            try:
                import torch
                import transformers
                logger.info("ML dependencies available, attempting offline analysis...")
                
                # Try Phi-2 model with timeout protection (Windows compatible)
                try:
                    import threading
                    import time
                    
                    result_container = {"result": None, "error": None, "completed": False}
                    
                    def load_and_run():
                        try:
                            from modules.phi2_inference import phi2_summarize
                            logger.info("Using Phi-2 model for offline analysis...")
                            result_container["result"] = phi2_summarize(prompt, max_tokens=300)
                            result_container["completed"] = True
                        except Exception as e:
                            result_container["error"] = str(e)
                            result_container["completed"] = True
                    
                    # Run with timeout using threading
                    thread = threading.Thread(target=load_and_run)
                    thread.daemon = True
                    thread.start()
                    thread.join(timeout=45)  # Increased to 45 seconds for model loading
                    
                    if not result_container["completed"]:
                        logger.warning("Phi-2 model loading timed out after 45 seconds, falling back to cloud AI")
                        # Don't raise error, just fall through to cloud AI
                    elif result_container["error"]:
                        logger.warning(f"Phi-2 model failed: {result_container['error']}, falling back to cloud AI")
                        # Don't raise error, just fall through to cloud AI
                    elif result_container["result"] and len(result_container["result"].strip()) > 10:
                        logger.info("Phi-2 analysis completed successfully")
                        return result_container["result"].strip()
                    else:
                        logger.warning("Phi-2 returned empty or very short result")
                        
                except (ImportError, TimeoutError, Exception) as e:
                    logger.warning(f"Phi-2 model failed: {e}")
                
            except ImportError:
                logger.warning("ML dependencies (torch/transformers) not available, skipping offline analysis")
                
        except Exception as e:
            logger.error(f"Offline AI analysis failed: {e}")
    
    # Try OpenAI API if offline failed or not requested
    if OPENAI_API_KEY:
        logger.info("Attempting OpenAI API analysis...")
        client = OpenAI(api_key=OPENAI_API_KEY)
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert system administrator analyzing log files for root cause analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content.strip()
                if result:
                    logger.info("OpenAI analysis completed successfully")
                    return result
                    
            except Exception as e:
                logger.warning(f"OpenAI attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    sleep_s = 2 ** attempt
                    logger.info(f"Retrying in {sleep_s} seconds...")
                    time.sleep(sleep_s)
                else:
                    logger.error("OpenAI RCA failed after retries: %s", traceback.format_exc())
                    return f"OpenAI RCA failed: {e}"
    else:
        logger.warning("No OpenAI API key found in environment.")

    # ----- FAILOVER -----
    return "AI analysis temporarily unavailable. Local models require GPU resources and cloud API key not configured."

# ----- Main API Function -----
def generate_summary(events, metadata=None, test_results=None, context=None, offline=True):
    """Main entry point for AI analysis - wrapper around analyze_with_ai"""
    return analyze_with_ai(events, metadata, test_results, context, offline)

# For standalone testing only
if __name__ == "__main__":
    class DummyEvent:
        def __init__(self, ts, sev, comp, msg):
            self.timestamp = ts
            self.severity = sev
            self.component = comp
            self.message = msg

    dummy_logs = [
        DummyEvent("2025-06-30 10:00:00", "ERROR", "Installer", "Failed to initialize deployment."),
        DummyEvent("2025-06-30 10:01:00", "INFO", "Service", "Restarted successfully."),
        DummyEvent("2025-06-30 10:02:00", "CRITICAL", "Boot", "System halted due to invalid signature.")
    ]
    dummy_meta = {"OS": "Win25H2", "Build": "26000"}
    dummy_results = [{"Step": "Install BIOS", "Status": "Fail", "Actual Result": "BIOS not detected"}]

    print("\n=== RCA Output ===")
    print(analyze_with_ai(dummy_logs, dummy_meta, dummy_results, offline=False))
