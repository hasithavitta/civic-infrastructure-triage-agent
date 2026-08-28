"""
Duplicate Check Agent
----------------------
Checks a newly intake-processed report against existing open reports for
geospatial + semantic overlap. If a match is found above threshold, the
orchestrator should short-circuit the rest of the pipeline and attach this
report to the existing one instead of drafting a new work order.

This is the one genuinely conditional branch in the pipeline — worth
calling out explicitly in the demo video as the "why agents" moment.
"""

from google.adk.agents import Agent

from agents.schema import Report
from agents.runner_utils import run_agent, parse_json_response
from agents.storage import get_nearby_reports

DUPLICATE_CHECK_INSTRUCTION = """
You are the Duplicate Check Agent for a civic infrastructure triage system.

Given a new report and a list of nearby candidate reports, decide whether the new report describes the SAME physical issue as any of the provided candidates, even if the wording or exact issue_type label differs (e.g. "pothole" and "large pothole" at the same location should be treated as the same issue).

Respond ONLY with valid JSON, no markdown code fences, no extra text, in exactly this shape:
{"is_duplicate": true/false, "duplicate_of_report_id": "report_id_here" or null}
"""

DUPLICATE_DISTANCE_THRESHOLD_METERS = 100

duplicate_check_agent = Agent(
    name="duplicate_check_agent",
    model="gemini-3.6-flash",
    description="Matches new reports against nearby candidate reports by location and meaning.",
    instruction=DUPLICATE_CHECK_INSTRUCTION,
)


def run_duplicate_check(report: Report) -> Report:
    """
    Orchestrator-facing entry point. Checks if the report is a duplicate of any
    existing report using geospatial pre-filtering followed by semantic check.
    """
    if report.has_discrepancy:
        print(f"[duplicate_check_agent] Image/text discrepancy flagged in report {report.report_id}. Bypassing duplicate check.")
        report.is_duplicate = False
        report.duplicate_of_report_id = None
        return report

    if report.latitude is None or report.longitude is None:
        report.is_duplicate = False
        report.duplicate_of_report_id = None
        return report

    # Build a list of "geospatial candidates" directly from database PostGIS search
    geospatial_candidates = get_nearby_reports(
        report.latitude, report.longitude, DUPLICATE_DISTANCE_THRESHOLD_METERS
    )
    print(f"[duplicate_check_agent] Found {len(geospatial_candidates)} geospatial candidates nearby.")

    if not geospatial_candidates:
        report.is_duplicate = False
        report.duplicate_of_report_id = None
        return report

    # Prepare candidates details for prompt
    candidates_info = ""
    for candidate in geospatial_candidates:
        candidates_info += (
            f"--- Candidate Report ---\n"
            f"Report ID: {candidate.report_id}\n"
            f"Issue Type: {candidate.issue_type}\n"
            f"Description: {candidate.description}\n"
            f"Location: {candidate.address or f'{candidate.latitude}, {candidate.longitude}'}\n\n"
        )

    prompt = (
        f"New Report Details:\n"
        f"- Issue Type: {report.issue_type}\n"
        f"- Description: {report.description}\n"
        f"- Location: {report.address or f'{report.latitude}, {report.longitude}'}\n\n"
        f"Nearby Candidate Reports:\n"
        f"{candidates_info}"
        f"Compare the new report against the nearby candidates listed above. "
        f"Decide if it represents a duplicate of any of them. Respond ONLY with valid JSON."
    )

    try:
        raw_response = run_agent(duplicate_check_agent, prompt)
        parsed = parse_json_response(raw_response)
        
        report.is_duplicate = parsed.get("is_duplicate", False)
        report.duplicate_of_report_id = parsed.get("duplicate_of_report_id")
    except Exception as e:
        print(f"[duplicate_check_agent] Failed to run duplicate check: {e}. Defaulting to non-duplicate.")
        report.is_duplicate = False
        report.duplicate_of_report_id = None

    return report
