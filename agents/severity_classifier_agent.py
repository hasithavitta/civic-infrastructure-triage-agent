"""
Severity Classifier Agent
--------------------------
Scores the urgency of a report on a 1-5 scale and — critically — explains
its reasoning. This explainability is the differentiator: a plain
classifier gives a label, this agent gives a department a reason they can
act on and a citizen a reason they can trust.
"""

from google.adk.agents import Agent

from agents.schema import Report
from agents.runner_utils import run_agent, parse_json_response
from mcp_server.geocoding_server import nearby_landmarks_core

SEVERITY_INSTRUCTION = """
You are the Severity Classifier Agent for a civic infrastructure triage system.

Given a report's issue type, description, and location context (including any nearby landmarks), assign a severity score from 1 (minor, cosmetic) to 5 (immediate safety hazard).

Base your score on factors like:
- Safety risk (e.g., a large pothole in a high-traffic area vs a minor crack on a quiet sidewalk).
- Proximity to vulnerable areas (e.g., schools, hospitals, busy pedestrian zones). If there are nearby schools or hospitals listed under location context, this should meaningfully raise the severity score of the issue.
- Likelihood of quick deterioration.

You MUST explain your reasoning in 1-2 plain-language sentences. Make sure the reasoning specifically references details from the citizen's report (e.g., specific street name, landmark, school, or vehicle swerving if mentioned). If a nearby landmark (school or hospital) is a factor in your score, you MUST explicitly mention that specific landmark by name in your reasoning, rather than vaguely referencing "nearby sensitive areas." Do not return generic text.

Respond ONLY with valid JSON, no markdown code fences, no extra text, in exactly this shape:
{"severity_score": number, "severity_reasoning": "reasoning_text"}
"""

severity_classifier_agent = Agent(
    name="severity_classifier_agent",
    model="gemini-2.5-flash",
    description="Assigns an explainable urgency score to a report.",
    instruction=SEVERITY_INSTRUCTION,
)


def run_severity_classification(report: Report) -> Report:
    """
    Orchestrator-facing entry point. Calls severity_classifier_agent via ADK and
    parses its structured JSON response to assign severity score and reasoning.
    """
    landmarks_str = ""
    if report.latitude is not None and report.longitude is not None:
        try:
            landmarks = nearby_landmarks_core(report.latitude, report.longitude)
            if landmarks:
                landmarks_str = "\nNearby landmarks within 200m:\n" + "\n".join(f"- {lm}" for lm in landmarks)
        except Exception as e:
            print(f"[severity_classifier_agent] Landmarks lookup exception: {e}")

    prompt = (
        f"Classify the severity of this report:\n"
        f"- Issue Type: {report.issue_type}\n"
        f"- Description: {report.description}\n"
        f"- Location: {report.address or f'{report.latitude}, {report.longitude}'}\n"
        f"{landmarks_str}"
    )

    try:
        raw_response = run_agent(severity_classifier_agent, prompt)
        parsed = parse_json_response(raw_response)
        
        score = parsed.get("severity_score", 3)
        try:
            report.severity_score = int(score)
        except (ValueError, TypeError):
            report.severity_score = 3
            
        report.severity_reasoning = parsed.get(
            "severity_reasoning", 
            "Failed to retrieve severity reasoning from the model."
        )
    except Exception as e:
        print(f"[severity_classifier_agent] Failed to run classification: {e}. Defaulting to fallback.")
        report.severity_score = 3
        report.severity_reasoning = f"Fallback severity reasoning due to classification failure: {e}"

    return report
