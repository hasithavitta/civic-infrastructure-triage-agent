"""
Smoke test for the MCP geocoding server's underlying functions.

Run this BEFORE wiring the MCP server into any agent — it tests the raw
geocoding/distance logic directly, without going through the MCP protocol,
so you can catch a bad address, a Nominatim rate limit, or a network
issue in isolation.

Run with:
    python tests/test_mcp_geocoding.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_server.geocoding_server import geocode_address, distance_meters


def test_geocode_known_address():
    result = geocode_address("Charminar, Hyderabad")
    print("geocode_address('Charminar, Hyderabad') ->", result)
    assert result["latitude"] is not None, "Geocoding failed — check network/Nominatim rate limits"
    assert result["longitude"] is not None


def test_geocode_garbage_input():
    result = geocode_address("asdkfjalksdjflaksjdf9999")
    print("geocode_address(garbage) ->", result)
    # Should not crash — should return None values gracefully
    assert result["latitude"] is None


def test_distance_meters():
    # Roughly Charminar to Golconda Fort, Hyderabad — should be a few km
    dist = distance_meters(17.3616, 78.4747, 17.3833, 78.4011)
    print("distance_meters(Charminar, Golconda) ->", dist, "meters")
    assert dist > 1000, "Distance seems too small for two distinct landmarks"


if __name__ == "__main__":
    print("Running MCP geocoding smoke tests...\n")
    test_geocode_known_address()
    test_geocode_garbage_input()
    test_distance_meters()
    print("\nAll smoke tests passed.")
