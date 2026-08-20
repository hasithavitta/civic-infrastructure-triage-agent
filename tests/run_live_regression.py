import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

# We can clear the database using the local Supabase client connection
from agents.storage import db

LIVE_URL = "https://civic-infrastructure-triage-agent.onrender.com/triage"
API_KEY = os.environ.get("TRIAGE_API_KEY") or os.environ.get("TRIAGE_DEMO_API_KEY")

headers = {
    "X-API-Key": API_KEY
}

def clear_db():
    try:
        db.table("reports").delete().neq("report_id", "").execute()
        print("Database reports cleared.")
    except Exception as e:
        print(f"Warning: Failed to clear database reports: {e}")

def run_live_tests():
    if not API_KEY:
        print("Error: TRIAGE_API_KEY or TRIAGE_DEMO_API_KEY not found in .env")
        sys.exit(1)
        
    print("======================================================================")
    print("LIVE TEST 1: Regression case (Charminar, different wording)")
    print("======================================================================")
    clear_db()
    
    # Report 1
    print("Sending Report 1 (Initial Report - Charminar) to live URL...")
    r1_resp = requests.post(
        LIVE_URL,
        data={"raw_text": "There is a massive crater in the road right in front of Charminar, Hyderabad."},
        headers=headers
    )
    print(f"Report 1 Response status: {r1_resp.status_code}")
    report1 = r1_resp.json()
    print(json.dumps(report1, indent=2))
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)
    
    # Report 2: different wording
    print("Sending Report 2 (Duplicate - Charminar) to live URL...")
    r2_resp = requests.post(
        LIVE_URL,
        data={"raw_text": "A small pothole is reported near Charminar, Hyderabad."},
        headers=headers
    )
    print(f"Report 2 Response status: {r2_resp.status_code}")
    report2 = r2_resp.json()
    print(json.dumps(report2, indent=2))
    
    assert report2.get("is_duplicate") is True, "Live Test 1 Failed: Should be marked as duplicate!"
    assert report2.get("duplicate_of_report_id") == report1.get("report_id"), f"Live Test 1 Failed: Should be duplicate of {report1.get('report_id')}"
    print("\n=> LIVE TEST 1 PASSED!")

    print("\n======================================================================")
    print("LIVE TEST 2: Proximity pre-filter (Same issue type, far apart)")
    print("======================================================================")
    clear_db()
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)

    # Report 1 again
    print("Sending Report 1 (Charminar) to live URL...")
    r1_resp = requests.post(
        LIVE_URL,
        data={"raw_text": "There is a pothole near Charminar, Hyderabad."},
        headers=headers
    )
    print(f"Report 1 Response status: {r1_resp.status_code}")
    report1 = r1_resp.json()
    print(json.dumps(report1, indent=2))
    
    print("\nSleeping for 30 seconds to respect API rate limits (RPM)...")
    time.sleep(30)

    # Report 3: far apart (India Gate, Delhi)
    print("Sending Report 3 (Far Away - India Gate) to live URL...")
    r3_resp = requests.post(
        LIVE_URL,
        data={"raw_text": "There is a pothole near India Gate, New Delhi."},
        headers=headers
    )
    print(f"Report 3 Response status: {r3_resp.status_code}")
    report3 = r3_resp.json()
    print(json.dumps(report3, indent=2))
    
    assert report3.get("is_duplicate") is False, "Live Test 2 Failed: Should NOT be marked as duplicate (too far apart)!"
    print("\n=> LIVE TEST 2 PASSED!")

if __name__ == "__main__":
    run_live_tests()
