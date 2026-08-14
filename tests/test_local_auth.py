import requests
import json
import sys

LOCAL_URL = "http://localhost:8080"
CORRECT_KEY = "Usm1Ax8wkHBPPySoMFBAZdx2cVIz5-V3F8qIBtPPgeo"

def run_tests():
    print("=========================================================")
    print("Starting Local Authentication Security Tests")
    print("=========================================================\n")
    
    # Test 1: POST /triage with NO key
    print("Test 1: POST /triage with NO key header")
    try:
        r1 = requests.post(f"{LOCAL_URL}/triage", data={"raw_text": "A pothole near the park."})
        print(f" -> Status Code: {r1.status_code}")
        print(f" -> Response Body: {r1.text}")
        assert r1.status_code == 401, f"Expected 401, got {r1.status_code}"
        assert "Invalid or missing API key" in r1.text
        print(" -> PASSED\n")
    except Exception as e:
        print(f" -> FAILED: {e}\n")
        sys.exit(1)
        
    # Test 2: POST /triage with WRONG key
    print("Test 2: POST /triage with WRONG key header")
    try:
        headers = {"X-API-Key": "wrong-key-123"}
        r2 = requests.post(f"{LOCAL_URL}/triage", data={"raw_text": "A pothole near the park."}, headers=headers)
        print(f" -> Status Code: {r2.status_code}")
        print(f" -> Response Body: {r2.text}")
        assert r2.status_code == 401, f"Expected 401, got {r2.status_code}"
        assert "Invalid or missing API key" in r2.text
        print(" -> PASSED\n")
    except Exception as e:
        print(f" -> FAILED: {e}\n")
        sys.exit(1)
        
    # Test 3: POST /triage with CORRECT key
    print("Test 3: POST /triage with CORRECT key header")
    try:
        headers = {"X-API-Key": CORRECT_KEY}
        # Use a simplified address for geocoding
        r3 = requests.post(
            f"{LOCAL_URL}/triage", 
            data={"raw_text": "A dangerous pothole has opened up on Raj Bhavan Road, Somajiguda, Hyderabad."}, 
            headers=headers
        )
        print(f" -> Status Code: {r3.status_code}")
        print(f" -> Response Body: {r3.text[:200]}... (truncated)")
        assert r3.status_code == 200, f"Expected 200, got {r3.status_code}"
        print(" -> PASSED\n")
    except Exception as e:
        print(f" -> FAILED: {e}\n")
        sys.exit(1)
        
    # Test 4: GET / (health check) with NO headers
    print("Test 4: GET / (health check) with NO headers")
    try:
        r4 = requests.get(f"{LOCAL_URL}/")
        print(f" -> Status Code: {r4.status_code}")
        print(f" -> Response Body: {r4.text}")
        assert r4.status_code == 200, f"Expected 200, got {r4.status_code}"
        print(" -> PASSED\n")
    except Exception as e:
        print(f" -> FAILED: {e}\n")
        sys.exit(1)
        
    print("All local security tests PASSED successfully!")

if __name__ == "__main__":
    run_tests()
