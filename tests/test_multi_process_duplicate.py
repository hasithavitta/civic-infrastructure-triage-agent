import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator import process_report

def run():
    if len(sys.argv) < 2:
        print("Usage: python test_multi_process_duplicate.py [step1|step2]")
        sys.exit(1)
        
    mode = sys.argv[1]
    
    if mode == "step1":
        print("=== STEP 1: Submitting initial report ===")
        # Prune database to ensure clean test
        from agents.storage import db
        docs = db.collection("reports").stream()
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        print(f"Cleared {count} existing records in Firestore.")
        
        # Submit first report (Yashoda Hospital, Somajiguda)
        report = process_report(
            raw_text="A dangerous pothole has opened up on Raj Bhavan Road, Somajiguda, Hyderabad."
        )
        print("Report 1 processed:")
        print(f"  ID: {report.report_id}")
        print(f"  Is Duplicate: {report.is_duplicate}")
        print(f"  Coordinates: ({report.latitude}, {report.longitude})")
        
        # Save the report ID for step 2 verification
        os.makedirs("tests", exist_ok=True)
        with open("tests/initial_report_id.txt", "w") as f:
            f.write(report.report_id)
            
    elif mode == "step2":
        print("=== STEP 2: Submitting duplicate report ===")
        if not os.path.exists("tests/initial_report_id.txt"):
            print("Error: Run step1 first.")
            sys.exit(1)
            
        with open("tests/initial_report_id.txt", "r") as f:
            initial_id = f.read().strip()
            
        # Submit duplicate report
        report = process_report(
            raw_text="There is a deep pothole on the road at Raj Bhavan Road, Somajiguda, Hyderabad, drivers are swerving."
        )
        print("Report 2 processed:")
        print(f"  ID: {report.report_id}")
        print(f"  Is Duplicate: {report.is_duplicate}")
        print(f"  Duplicate Of: {report.duplicate_of_report_id}")
        
        # Verify duplicate detection succeeded
        if report.is_duplicate and report.duplicate_of_report_id == initial_id:
            print("\n=== SUCCESS ===")
            print("Successfully detected duplicate across separate process runs!")
        else:
            print("\n=== FAILURE ===")
            print(f"Expected duplication of {initial_id}, got is_duplicate={report.is_duplicate}, duplicate_of={report.duplicate_of_report_id}")
            sys.exit(1)

if __name__ == "__main__":
    run()
