import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.schema import Report
from agents.storage import save_report

def run_save():
    print("Saving test report to Supabase...")
    report_id = f"test-report-{uuid.uuid4()}"
    report = Report(
        raw_text="This is a persistent storage unit test.",
        issue_type="pothole",
        description="Pothole on the test road.",
        latitude=12.34,
        longitude=56.78,
        address="Test Road 123",
        is_duplicate=False,
        severity_score=2,
        severity_reasoning="Minor damage, low hazard.",
        department="Test Department",
        work_order_text="DRAFT WORK ORDER",
        report_id=report_id
    )
    save_report(report)
    print(f"Report {report_id} successfully saved.")
    
    # Write the report_id to a temp file so the read script knows what ID to look for
    os.makedirs("tests", exist_ok=True)
    with open("tests/saved_report_id.txt", "w") as f:
        f.write(report_id)

if __name__ == "__main__":
    run_save()
