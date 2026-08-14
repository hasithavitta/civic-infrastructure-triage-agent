import pytest
from agents.duplicate_check_agent import run_duplicate_check, _is_within_duplicate_radius

def test_is_within_duplicate_radius(report_factory):
    # Coords matching exactly (0m)
    r1 = report_factory(latitude=17.4245627, longitude=78.4569401)
    r2 = report_factory(latitude=17.4245627, longitude=78.4569401)
    assert _is_within_duplicate_radius(r1, r2) is True
    
    # Coordinates in Delhi, India Gate (lat=28.6129, lon=77.2295) -> way outside threshold
    r3 = report_factory(latitude=28.6129, longitude=77.2295)
    assert _is_within_duplicate_radius(r1, r3) is False
    
    # Reports with None coordinates
    r4 = report_factory(latitude=None, longitude=None)
    assert _is_within_duplicate_radius(r1, r4) is False

def test_duplicate_check_empty_database(mock_gemini, report_factory):
    report = report_factory()
    res = run_duplicate_check(report, [])
    assert res.is_duplicate is False
    mock_gemini.duplicate.assert_not_called()

def test_duplicate_check_far_away(mock_gemini, report_factory):
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    existing = [report_factory(latitude=28.6129, longitude=77.2295, report_id="delhi-report")]
    
    res = run_duplicate_check(report, existing)
    
    assert res.is_duplicate is False
    mock_gemini.duplicate.assert_not_called()

def test_duplicate_check_nearby_match(mock_gemini, mock_geocoding, report_factory):
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    existing = [report_factory(latitude=17.4245627, longitude=78.4569401, report_id="match-report")]
    
    mock_geocoding.distance.return_value = 5.0
    mock_gemini.set_response('{"is_duplicate": true, "duplicate_of_report_id": "match-report"}')
    
    res = run_duplicate_check(report, existing)
    
    assert res.is_duplicate is True
    assert res.duplicate_of_report_id == "match-report"
    mock_gemini.duplicate.assert_called_once()

def test_duplicate_check_malformed_fallback(mock_gemini, mock_geocoding, report_factory):
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    existing = [report_factory(latitude=17.4245627, longitude=78.4569401, report_id="match-report")]
    
    mock_geocoding.distance.return_value = 5.0
    mock_gemini.set_response("broken-json-response")
    
    res = run_duplicate_check(report, existing)
    
    assert res.is_duplicate is False
    assert res.duplicate_of_report_id is None
