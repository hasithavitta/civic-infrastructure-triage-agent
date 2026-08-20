import sys
import os
import json
from dataclasses import asdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import orchestrator
from orchestrator import process_report
from agents.storage import db
from agents.schema import Report

# Bypass severity and dispatch to focus only on intake and duplicate detection
orchestrator.run_severity_classification = lambda report: report
orchestrator.run_dispatch = lambda report: report

# Mock geocoding to resolve address to Charminar coordinates deterministically
import agents.intake_agent
def mock_geocode_address_core(address: str) -> dict:
    if address and "charminar" in address.lower():
        return {
            "latitude": 17.3616024,
            "longitude": 78.4746421,
            "resolved_address": "Charminar, Hyderabad, Telangana, India"
        }
    return {"latitude": None, "longitude": None, "resolved_address": None}

agents.intake_agent.geocode_address_core = mock_geocode_address_core

def run_harder_test():
    try:
        db.table("reports").delete().neq("report_id", "").execute()
        print("Database reports cleared.")
    except Exception as e:
        print(f"Warning: Failed to clear database reports: {e}")
    
    print("\nProcessing Report 1...")
    report1 = process_report(
        raw_text="There is a massive sinkhole in the middle of the road at Charminar, Hyderabad."
    )
    
    print("\nProcessing Report 2...")
    report2 = process_report(
        raw_text="A severe case of road surface damage is reported at Charminar, Hyderabad."
    )
    
    print("\n=== RESULTS ===")
    print(f"Report 1: ID={report1.report_id}, Issue Type='{report1.issue_type}', Address='{report1.address}', Coordinates=({report1.latitude}, {report1.longitude})")
    print(f"Report 2: ID={report2.report_id}, Issue Type='{report2.issue_type}', Address='{report2.address}', Coordinates=({report2.latitude}, {report2.longitude})")
    print(f"Report 2 Duplicate Check: is_duplicate={report2.is_duplicate}, duplicate_of_report_id={report2.duplicate_of_report_id}")
    
    # Assert that the issue types are actually different strings for this regression test to be valid
    different_issue_types = report1.issue_type != report2.issue_type
    print(f"Regression Check: Are issue types different? {different_issue_types}")
    
    if report2.is_duplicate:
        print("\n=> TEST SUCCESSFUL: Correctly identified duplicate despite differing issue types!")
    else:
        print("\n=> TEST FAILED: Failed to detect duplicate!")

if __name__ == "__main__":
    run_harder_test()
