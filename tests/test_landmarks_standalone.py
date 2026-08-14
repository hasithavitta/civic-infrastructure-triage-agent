import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_server.geocoding_server import geocode_address_core, nearby_landmarks_core

def run_standalone_tests():
    print("=========================================================")
    print("1. Standalone Test: Geocoding and Landmark Proximity")
    print("=========================================================")
    
    # Geocode a known hospital in Hyderabad
    address = "Yashoda Hospital, Somajiguda, Hyderabad"
    print(f"Geocoding address: '{address}'")
    geo_res = geocode_address_core(address)
    print("Geocoding result:", geo_res)
    
    lat = geo_res.get("latitude")
    lon = geo_res.get("longitude")
    
    if lat and lon:
        print(f"\nQuerying nearby landmarks within 300m for coordinates: ({lat}, {lon})")
        landmarks = nearby_landmarks_core(lat, lon, radius_meters=300)
        print(f"Found {len(landmarks)} landmarks:")
        for lm in landmarks:
            print(" -", lm)
    else:
        print("Error: Geocoding failed, cannot test nearby landmarks.")
        
    print("\n=========================================================")
    print("2. Standalone Test: Remote Rural Area (Middle of Nowhere)")
    print("=========================================================")
    # Coordinates in a remote field (lat=17.0, lon=78.0)
    rural_lat, rural_lon = 17.0, 78.0
    print(f"Querying nearby landmarks for rural coordinates: ({rural_lat}, {rural_lon})")
    rural_landmarks = nearby_landmarks_core(rural_lat, rural_lon, radius_meters=200)
    print("Found landmarks:", rural_landmarks)
    assert len(rural_landmarks) == 0, "Expected 0 landmarks in rural area!"
    print("=> Rural test passed successfully!")

if __name__ == "__main__":
    run_standalone_tests()
