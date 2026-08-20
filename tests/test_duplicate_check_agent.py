import pytest
from agents.duplicate_check_agent import run_duplicate_check

def test_duplicate_check_empty_database(mock_gemini, mock_storage, report_factory):
    mock_storage.clear()
    report = report_factory()
    res = run_duplicate_check(report)
    assert res.is_duplicate is False
    mock_gemini.duplicate.assert_not_called()

def test_duplicate_check_far_away(mock_gemini, mock_storage, mock_geocoding, report_factory):
    mock_storage.clear()
    mock_storage.save(report_factory(latitude=28.6129, longitude=77.2295, report_id="delhi-report"))
    
    # Coordinates in Delhi, India Gate -> far away from mock report coords in Somajiguda
    mock_geocoding.distance.return_value = 500000.0
    
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    res = run_duplicate_check(report)
    
    assert res.is_duplicate is False
    mock_gemini.duplicate.assert_not_called()

def test_duplicate_check_nearby_match(mock_gemini, mock_geocoding, mock_storage, report_factory):
    mock_storage.clear()
    mock_storage.save(report_factory(latitude=17.4245627, longitude=78.4569401, report_id="match-report"))
    
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    
    mock_geocoding.distance.return_value = 5.0
    mock_gemini.set_response('{"is_duplicate": true, "duplicate_of_report_id": "match-report"}')
    
    res = run_duplicate_check(report)
    
    assert res.is_duplicate is True
    assert res.duplicate_of_report_id == "match-report"
    mock_gemini.duplicate.assert_called_once()

def test_duplicate_check_malformed_fallback(mock_gemini, mock_geocoding, mock_storage, report_factory):
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    mock_storage.clear()
    mock_storage.save(report_factory(latitude=17.4245627, longitude=78.4569401, report_id="match-report"))
    
    mock_geocoding.distance.return_value = 5.0
    mock_gemini.set_response("broken-json-response")
    
    res = run_duplicate_check(report)
    
    assert res.is_duplicate is False
    assert res.duplicate_of_report_id is None

