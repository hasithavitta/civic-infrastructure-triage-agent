import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.storage import get_all_reports

def run_load():
    print("Loading reports from Firestore...")
    # Read the expected report_id from temp file
    if not os.path.exists("tests/saved_report_id.txt"):
        print("Error: No saved report ID found. Run save script first.")
        sys.exit(1)
        
    with open("tests/saved_report_id.txt", "r") as f:
        expected_id = f.read().strip()
        
    reports = get_all_reports()
    print(f"Total reports fetched: {len(reports)}")
    
    found = None
    for r in reports:
        if r.report_id == expected_id:
            found = r
            break
            
    if found:
        print("\n=== SUCCESS ===")
        print(f"Found saved report with ID: {found.report_id}")
        print(f"Raw Text: {found.raw_text}")
        print(f"Issue Type: {found.issue_type}")
        print(f"Location: {found.address} ({found.latitude}, {found.longitude})")
        print(f"Severity: {found.severity_score} - {found.severity_reasoning}")
    else:
        print("\n=== FAILURE ===")
        print(f"Expected report ID {expected_id} was NOT found in Firestore.")
        sys.exit(1)

if __name__ == "__main__":
    run_load()
