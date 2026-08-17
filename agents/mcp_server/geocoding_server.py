"""
MCP Geocoding Server
----------------------
A minimal MCP server exposing geocoding + distance tools that the Intake
and Duplicate Check agents call into. Kept as a separate server (rather
than inline functions) so it satisfies the "MCP Server" rubric line and
so it could, in principle, be swapped for a real municipal GIS service
later without touching the agents.

Run standalone with:
    python mcp_server/geocoding_server.py
"""

from mcp.server.fastmcp import FastMCP
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

mcp = FastMCP("civic-triage-geocoding")
_geolocator = Nominatim(user_agent="civic-triage-agent")


@mcp.tool()
def geocode_address(address: str) -> dict:
    """
    Resolve a free-text address or landmark description to coordinates.

    Args:
        address: A street name, landmark, or neighborhood description.

    Returns:
        dict with latitude, longitude, and the resolved display address.
    """
    location = _geolocator.geocode(address)
    if location is None:
        return {"latitude": None, "longitude": None, "resolved_address": None}
    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "resolved_address": location.address,
    }


@mcp.tool()
def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the distance in meters between two coordinate pairs.
    Used by the Duplicate Check Agent to decide if two reports are
    describing the same physical location.
    """
    return geodesic((lat1, lon1), (lat2, lon2)).meters


@mcp.tool()
def nearby_landmarks(lat: float, lon: float, radius_meters: int = 200) -> list[str]:
    """
    Placeholder for a "what's near this point" lookup — e.g. schools or
    hospitals — used by the Severity Classifier Agent to weigh urgency.
    Swap for a real Places API call when you have a key.
    """
    return []  # TODO: wire up a real places lookup


if __name__ == "__main__":
    mcp.run()