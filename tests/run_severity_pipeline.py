import sys
import os
import json
from dataclasses import asdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import orchestrator
import orchestrator
from orchestrator import process_report, EXISTING_REPORTS

def run_pipeline_test():
    EXISTING_REPORTS.clear()
    
    # We use a real address near a known hospital in Hyderabad
    raw_text = "A massive crater is reported right in the road at Yashoda Hospital, Somajiguda, Hyderabad."
    print(f"Running pipeline test for report: '{raw_text}'")
    
    try:
        # Run the full orchestrator pipeline end-to-end
        report = process_report(raw_text=raw_text)
        
        print("\n=== FINAL Structured Report JSON ===")
        print(json.dumps(asdict(report), indent=2))
        
        # Verify the landmarks query worked and was included in reasoning
        print("\n=== Verification ===")
        print("Resolved Address:", report.address)
        print("Coordinates:", (report.latitude, report.longitude))
        print("Severity Score:", report.severity_score)
        print("Severity Reasoning:", report.severity_reasoning)
        print("Assigned Department:", report.department)
        
    except Exception as e:
        print("Pipeline test execution failed:", e)

if __name__ == "__main__":
    run_pipeline_test()
