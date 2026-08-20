"""
Orchestrator
------------
Wires the four agents into a pipeline: mostly sequential, with one
conditional branch — if the Duplicate Check Agent finds a match, the
pipeline short-circuits and skips severity/dispatch in favor of attaching
to the existing report.

Pipeline: Intake -> Duplicate Check -> [branch] -> Severity -> Dispatch

This branch is the clearest "why agents, not a script" moment in the
project — call it out in the demo video. The Dispatch Agent merges what
used to be two separate agents (routing + work order drafting) into one
call, cutting a state-handoff point and an LLM round-trip.
"""

from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ — works regardless of terminal/IDE settings
import os
print("DEBUG key loaded:", os.environ.get("GOOGLE_API_KEY", "NOT FOUND")[:8], "...")

from agents.intake_agent import run_intake
from agents.duplicate_check_agent import run_duplicate_check
from agents.severity_classifier_agent import run_severity_classification
from agents.dispatch_agent import run_dispatch
from agents.schema import Report
from agents.storage import save_report


def process_report(
    raw_text: str | None = None,
    image_filename: str | None = None,
    image_bytes: bytes | None = None,
    image_mime_type: str | None = None,
) -> Report:
    """Runs a single citizen report through the full triage pipeline."""
    import uuid

    report = Report(
        raw_text=raw_text,
        image_filename=image_filename,
        report_id=str(uuid.uuid4()),
    )

    stage = "Intake"
    try:
        report = run_intake(
            raw_text=raw_text,
            image_filename=image_filename,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type,
        )


        stage = "Duplicate Check"
        report = run_duplicate_check(report)

        if report.is_duplicate:
            print(
                f"[orchestrator] Report {report.report_id} matches existing "
                f"report {report.duplicate_of_report_id} — attaching instead "
                f"of drafting a new work order."
            )
            save_report(report)
            return report

        stage = "Severity Classification"
        report = run_severity_classification(report)

        stage = "Dispatch"
        report = run_dispatch(report)

        save_report(report)
        return report
    except Exception as e:
        print(f"[orchestrator] Pipeline failed at {stage}: {e}")
        return report


if __name__ == "__main__":
    print("--- Running Report 1 (Initial Report) ---")
    sample1 = process_report(
        raw_text="There's a huge pothole on Main Street right outside the "
        "elementary school, cars are swerving to avoid it.",
    )
    print(sample1.work_order_text or "Attached as duplicate — no new work order drafted.")
    
    print("\n--- Running Report 2 (Potential Duplicate Report) ---")
    sample2 = process_report(
        raw_text="A dangerous pothole on Main Street in front of the elementary school is forcing drivers to swerve.",
    )
    print(sample2.work_order_text or "Attached as duplicate — no new work order drafted.")
