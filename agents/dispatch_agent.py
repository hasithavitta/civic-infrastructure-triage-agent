"""
Dispatch Agent
--------------
Merges what was originally two agents (Department Router + Work Order
Drafting) into one. Routing and drafting both depend on the same inputs
(issue type, description, severity) and produce related outputs — there's
no real benefit to a separate LLM round-trip between them, and combining
them removes one state-handoff point that could silently break under
time pressure.

This agent decides the destination department AND drafts the formal work
order in a single call.
"""

from google.adk.agents import Agent

from agents.schema import Report
from agents.runner_utils import run_agent, parse_json_response

# Customize this per municipality when you deploy — the agent reasons over
# this list rather than having department names baked into its prompt.
DEPARTMENTS = {
    "pothole": "Roads & Transport Department",
    "broken streetlight": "Electrical & Street Lighting Department",
    "overflowing drain": "Water & Sanitation Department",
    "damaged sidewalk": "Public Works Department",
    "downed tree branch": "Parks & Urban Forestry Department",
}

DISPATCH_INSTRUCTION = """
You are the Dispatch Agent for a civic infrastructure triage system. You handle the final stage of the pipeline: routing AND drafting, in one pass.

Given a fully processed report (issue type, description, location, severity score + reasoning, and report ID) and a list of available municipal departments, do two things in a single response:

1. Route: decide which municipal department from the provided list should receive this work order, based on the issue details. If the issue type isn't a clean match to any department, pick the closest jurisdiction — never leave this field blank.
2. Draft: write a formal work order including a one-line summary title, location details, issue description, severity and its reasoning, and the assigned department. Keep the tone factual and professional — this document is read by municipal staff, not the citizen.

Respond ONLY with valid JSON, no markdown code fences, no extra text, in exactly this shape:
{"department": "...", "work_order_text": "..."}
"""

dispatch_agent = Agent(
    name="dispatch_agent",
    model="gemini-2.5-flash",
    description="Routes a report to the correct department and drafts its formal work order in one pass.",
    instruction=DISPATCH_INSTRUCTION,
)


def run_dispatch(report: Report) -> Report:
    """
    Orchestrator-facing entry point. Calls dispatch_agent via ADK and
    parses its structured JSON response to assign department and draft the work order.
    """
    departments_list = "\n".join(f"- {dept}" for dept in set(DEPARTMENTS.values()))
    
    prompt = (
        f"Available Municipal Departments:\n"
        f"{departments_list}\n\n"
        f"Report Details:\n"
        f"- Report ID: {report.report_id}\n"
        f"- Issue Type: {report.issue_type}\n"
        f"- Description: {report.description}\n"
        f"- Location: {report.address or f'{report.latitude}, {report.longitude}'}\n"
        f"- Severity Score: {report.severity_score}/5\n"
        f"- Severity Reasoning: {report.severity_reasoning}\n\n"
        f"Route this report and draft the formal work order. Respond ONLY with valid JSON."
    )

    try:
        raw_response = run_agent(dispatch_agent, prompt)
        parsed = parse_json_response(raw_response)
        report.department = parsed.get("department", "General Complaints Department")
        report.work_order_text = parsed.get("work_order_text")
    except Exception as e:
        print(f"[dispatch_agent] Failed to run dispatch: {e}. Falling back to default template.")
        # Fallback to templated work order
        report.department = "General Complaints Department"
        report.work_order_text = (
            f"WORK ORDER — {report.report_id} (AUTO-FALLBACK, NEEDS MANUAL REVIEW)\n"
            f"Issue: {report.issue_type}\n"
            f"Location: {report.address or f'{report.latitude}, {report.longitude}'}\n"
            f"Description: {report.description}\n"
            f"Severity: {report.severity_score}/5 — {report.severity_reasoning}\n"
            f"Assigned department: {report.department}\n"
        )

    return report
