# ai_rca.py - Hybrid AI RCA using offline LLM and OpenAI fallback

from openai import OpenAI
import traceback
import logging
import os
import time
from dotenv import load_dotenv
from modules.phi2_inference_lora import phi2_summarize  # auto-loads LoRA if present

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
            "List up to 5 major ERROR or CRITICAL entries. Include timestamp, component, and brief description.\n\n"

            "4. **Root Cause Analysis**  \n"
            "Explain what most likely caused the failure(s). Consider the user's context and recent changes.\n\n"

            "5. **Targeted Fixes**  \n"
            "Give practical recommendations specific to the user's environment and deployment method.\n\n"

            "6. **Severity & Impact Rating**  \n"
            "Rate the severity as LOW / MEDIUM / HIGH and justify based on user's business impact.\n\n"

            "7. **Prevention & Monitoring**  \n"
            "Suggest how to prevent this issue and what to monitor going forward.\n\n"

            "If no serious issues are detected, focus on the user's reported symptoms and suggest investigation areas.\n"
            "Keep your answer structured, clean, and technical. Use bullet points for lists when helpful.\n\n"
        )
 
    log_text = format_logs_for_ai(events, metadata, test_results, context)
    safe_prompt = log_text[:2048]  # Increased limit for more context
    prompt += safe_prompt

    # ----- OFFLINE MODE (Phi-2 or legacy) -----
    if offline:
        try:
            if MODEL_BACKEND == "phi2":
                logger.info("Running Phi-2 offline RCA (with optional LoRA)...")
                completion = phi2_summarize(prompt, max_tokens=250)
                return completion or ""
            else:
                # Legacy path kept for one release; lazy import to avoid heavy deps
                logger.info("Running legacy offline RCA (DistilGPT-2)...")
                from legacy.distil_pipeline import legacy_generate
                return legacy_generate(safe_prompt, max_new_tokens=250)
        except Exception as e:
            logger.error(f"Offline model failed: {e}")
            return "Offline model failed. Try enabling OpenAI fallback if available."

    # ----- OPENAI MODE -----
    if OPENAI_API_KEY:
        # Retry with exponential backoff, avoid logging prompt content
        client = OpenAI(api_key=OPENAI_API_KEY)
        attempts = 3
        backoff = 1.5
        for i in range(attempts):
            try:
                logger.info("Using OpenAI for RCA (attempt %d/%d)...", i + 1, attempts)
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    temperature=0.4,
                    timeout=OPENAI_TIMEOUT,
                    messages=[
                        {"role": "system", "content": "You are a helpful QA and RCA assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                # Log exception type without prompt/body
                logger.error("OpenAI RCA attempt %d failed: %s", i + 1, e.__class__.__name__)
                if i < attempts - 1:
                    sleep_s = backoff ** i
                    time.sleep(sleep_s)
                else:
                    logger.error("OpenAI RCA failed after retries: %s", traceback.format_exc())
                    return f"OpenAI RCA failed: {e}"
    else:
        logger.warning("No OpenAI API key found in environment.")

    # ----- FAILOVER -----
    return "No valid AI engine configured. Please set OPENAI_API_KEY in .env or enable offline mode."

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
