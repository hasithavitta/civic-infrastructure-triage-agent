import sys
import os
import json
import time
from dataclasses import asdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import orchestrator first
import orchestrator
from orchestrator import process_report, EXISTING_REPORTS
from agents.schema import Report

# Monkeypatch/mock severity and dispatch to bypass rate limits and speed up tests
orchestrator.run_severity_classification = lambda report: report
orchestrator.run_dispatch = lambda report: report

# Monkeypatch/mock geocoding to resolve descriptive addresses to exact coordinates deterministically
import agents.intake_agent
def mock_geocode_address_core(address: str) -> dict:
    if not address:
        return {"latitude": None, "longitude": None, "resolved_address": None}
    addr_lower = address.lower()
    if "charminar" in addr_lower:
        return {
            "latitude": 17.3616024,
            "longitude": 78.4746421,
            "resolved_address": "Charminar, Hyderabad, Telangana, India"
        }
    if "india gate" in addr_lower:
        return {
            "latitude": 28.6129,
            "longitude": 77.2295,
            "resolved_address": "India Gate, New Delhi, Delhi, India"
        }
    return {"latitude": None, "longitude": None, "resolved_address": None}

agents.intake_agent.geocode_address_core = mock_geocode_address_core

def print_json(label: str, report: Report):
    print(f"\n=== {label} ===")
    print(json.dumps(asdict(report), indent=2))

def run_tests():
    EXISTING_REPORTS.clear()

    print("======================================================================")
    print("TEST 1: Regression case (Charminar, different wording)")
    print("======================================================================")
    
    # Report 1
    report1 = process_report(
        raw_text="There is a massive crater in the road right in front of Charminar, Hyderabad."
    )
    print_json("Report 1 (Initial Report - Charminar)", report1)
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)
    
    # Report 2: different wording ("small pothole" vs "massive crater")
    report2 = process_report(
        raw_text="A small pothole is reported near Charminar, Hyderabad."
    )
    print_json("Report 2 (Duplicate - Charminar)", report2)
    
    assert report2.is_duplicate is True, "Test 1 Failed: Should be marked as duplicate!"
    assert report2.duplicate_of_report_id == report1.report_id, f"Test 1 Failed: Should be duplicate of {report1.report_id}"
    print("\n=> TEST 1 PASSED!")

    print("\n======================================================================")
    print("TEST 2: Proximity pre-filter (Same issue type, far apart)")
    print("======================================================================")
    EXISTING_REPORTS.clear()
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)

    # Report 1 again
    report1 = process_report(
        raw_text="There is a pothole near Charminar, Hyderabad."
    )
    print_json("Report 1 (Charminar)", report1)
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)

    # Report 3: far apart (India Gate, Delhi)
    report3 = process_report(
        raw_text="There is a pothole near India Gate, New Delhi."
    )
    print_json("Report 3 (Far Away - India Gate)", report3)
    
    assert report3.is_duplicate is False, "Test 2 Failed: Should NOT be marked as duplicate (too far apart)!"
    print("\n=> TEST 2 PASSED!")

    print("\n======================================================================")
    print("TEST 3: Null address / coordinates report")
    print("======================================================================")
    EXISTING_REPORTS.clear()
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)

    # Report 1 again
    report1 = process_report(
        raw_text="There is a pothole near Charminar, Hyderabad."
    )
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)

    # Report 4: no address / coordinates
    report4 = process_report(
        raw_text="There is a pothole."
    )
    print_json("Report 4 (Null Coordinates)", report4)
    
    assert report4.is_duplicate is False, "Test 3 Failed: Null location report should not be marked as duplicate!"
    print("\n=> TEST 3 PASSED!")

if __name__ == "__main__":
    run_tests()
