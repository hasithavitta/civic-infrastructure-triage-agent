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
from mcp_server.geocoding_server import distance_meters_core

DUPLICATE_CHECK_INSTRUCTION = """
You are the Duplicate Check Agent for a civic infrastructure triage system.

Given a new report and a list of nearby candidate reports, decide whether the new report describes the SAME physical issue as any of the provided candidates, even if the wording or exact issue_type label differs (e.g. "pothole" and "large pothole" at the same location should be treated as the same issue).

Respond ONLY with valid JSON, no markdown code fences, no extra text, in exactly this shape:
{"is_duplicate": true/false, "duplicate_of_report_id": "report_id_here" or null}
"""

DUPLICATE_DISTANCE_THRESHOLD_METERS = 100

duplicate_check_agent = Agent(
    name="duplicate_check_agent",
    model="gemini-flash-latest",
    description="Matches new reports against nearby candidate reports by location and meaning.",
    instruction=DUPLICATE_CHECK_INSTRUCTION,
)


def _is_within_duplicate_radius(r1: Report, r2: Report) -> bool:
    """
    Checks if two reports are within DUPLICATE_DISTANCE_THRESHOLD_METERS (100 meters).
    Both reports must have non-null latitude and longitude.
    """
    if r1.latitude is None or r1.longitude is None or r2.latitude is None or r2.longitude is None:
        return False
    try:
        dist = distance_meters_core(r1.latitude, r1.longitude, r2.latitude, r2.longitude)
        return dist <= DUPLICATE_DISTANCE_THRESHOLD_METERS
    except Exception as e:
        print(f"[duplicate_check_agent] Error calculating distance between reports: {e}")
        return False


def run_duplicate_check(report: Report, existing_reports: list[Report]) -> Report:
    """
    Orchestrator-facing entry point. Checks if the report is a duplicate of any
    existing report using geospatial pre-filtering followed by semantic check.
    """
    if not existing_reports or report.latitude is None or report.longitude is None:
        report.is_duplicate = False
        report.duplicate_of_report_id = None
        return report

    # Build a list of "geospatial candidates"
    geospatial_candidates = [
        r for r in existing_reports
        if _is_within_duplicate_radius(report, r)
    ]

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
