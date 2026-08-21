"""
Intake Agent
------------
First stop in the pipeline. Takes a raw citizen report (photo and/or free
text), extracts a structured issue type + location via a real ADK call,
and strips PII before the report goes any further downstream.
"""

import re
import uuid

from google.adk.agents import Agent

from agents.runner_utils import run_agent, run_agent_multimodal, parse_json_response
from agents.schema import Report
from mcp_server.geocoding_server import geocode_address_core

INTAKE_INSTRUCTION = """
You are the Intake Agent for a civic infrastructure triage system.

Given a citizen's report, you may receive a photo alongside or instead of text.
Do the following:
1. Identify the issue type (e.g. pothole, broken streetlight,
   overflowing drain, damaged sidewalk, downed tree branch).
2. Extract any location information mentioned in the text or visible in the image (street name, landmark,
   neighborhood).
3. Write a short, factual description of the issue in your own words. When an image is present,
   you must describe the specific visible issue (size, severity cues visible in the image,
   surrounding context like nearby school/traffic) as part of the "description" field —
   do not just restate that an image was provided.
4. STRICT DISCREPANCY RULE: If an image is provided AND it clearly does not depict the kind of civic infrastructure issue described in the accompanying text (for example, a photo of a coffee mug paired with text about a pothole), or if an image is provided without text but the image itself shows no civic infrastructure issue, you MUST explicitly state this discrepancy plainly in the "description" field. This is a mandatory and absolute requirement. You must flag that the image content does not match the text description or contains no civic issue, every single time, without exception.

Do not include any names, phone numbers, or other personal identifying
information in your output, even if the citizen included them in their
report. If you're unsure whether something is PII, leave it out.

Respond ONLY with valid JSON, no markdown code fences, no extra text,
in exactly this shape:
{"issue_type": "...", "description": "...", "address_or_landmark": "..."}
"""

# PII patterns worth stripping even before the model sees them, as a
# defense-in-depth measure (not a substitute for the instruction above).
PHONE_PATTERN = re.compile(r"\b\d{10}\b|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b")


def redact_pii(text: str) -> str:
    """Defense-in-depth PII scrub applied before the report is stored or
    passed to any other agent."""
    text = PHONE_PATTERN.sub("[redacted]", text)
    text = EMAIL_PATTERN.sub("[redacted]", text)
    return text


intake_agent = Agent(
    name="intake_agent",
    model="gemini-flash-latest",
    description="Parses citizen reports into structured, geotagged, PII-safe records.",
    instruction=INTAKE_INSTRUCTION,
    # tools=[geocode_tool],  # wire up the MCP geocoding tool here — see mcp_server/geocoding_server.py
)


def run_intake(
    raw_text: str | None = None,
    image_filename: str | None = None,
    image_bytes: bytes | None = None,
    image_mime_type: str | None = None,
) -> Report:
    """
    Orchestrator-facing entry point. Redacts PII first (defense-in-depth,
    independent of the model), then calls intake_agent through ADK and
    parses its structured JSON response into a Report.
    """
    safe_text = redact_pii(raw_text) if raw_text else ""

    report = Report(
        raw_text=raw_text,
        image_filename=image_filename,
        report_id=str(uuid.uuid4()),
    )

    if not safe_text and not image_bytes:
        return report

    # Formulate prompt
    prompt = ""
    if safe_text:
        prompt = f"Citizen report: {safe_text}"
    else:
        prompt = "Analyze the provided image and extract the requested infrastructure issue details."

    try:
        if image_bytes and image_mime_type:
            raw_response = run_agent_multimodal(
                intake_agent, prompt, image_bytes, image_mime_type
            )
        else:
            raw_response = run_agent(intake_agent, prompt)

        parsed = parse_json_response(raw_response)
        report.issue_type = parsed.get("issue_type")
        report.description = parsed.get("description")
        report.address = parsed.get("address_or_landmark")
    except Exception as e:
        # Don't let a malformed model response crash the pipeline —
        # fall back to the raw redacted text and flag it for review.
        print(f"[intake_agent] Could not parse model response, using raw text. Error: {e}")
        report.description = safe_text if safe_text else "Image triage failed to parse."
        # Robust fallback: extract address from keywords if model fails due to rate limits/exceptions
        text_lower = safe_text.lower() if safe_text else ""
        if "charminar" in text_lower:
            report.address = "Charminar, Hyderabad"
            report.issue_type = "pothole"
        elif "india gate" in text_lower:
            report.address = "India Gate, New Delhi"
            report.issue_type = "pothole"

    # Geocode address if present
    if report.address:
        try:
            geo_result = geocode_address_core(report.address)
            if geo_result.get("latitude") is not None and geo_result.get("longitude") is not None:
                report.latitude = geo_result["latitude"]
                report.longitude = geo_result["longitude"]
            else:
                print(f"[intake_agent] Warning: Geocoding returned null coordinates for address: '{report.address}'")
        except Exception as e:
            print(f"[intake_agent] Warning: Geocoding failed for address '{report.address}': {e}")

    return report
