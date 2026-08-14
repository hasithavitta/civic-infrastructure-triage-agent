import pytest
from agents.severity_classifier_agent import run_severity_classification

def test_severity_with_landmarks(mock_gemini, mock_geocoding, report_factory):
    mock_geocoding.landmarks.return_value = ["Hospital: Yashoda Hospital (~7m away)"]
    mock_gemini.set_response('{"severity_score": 5, "severity_reasoning": "Near Yashoda Hospital."}')
    
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    run_severity_classification(report)
    
    prompt_sent = mock_gemini.severity.call_args[0][1]
    assert "Nearby landmarks within 200m:" in prompt_sent
    assert "Hospital: Yashoda Hospital (~7m away)" in prompt_sent
    assert report.severity_score == 5
    assert report.severity_reasoning == "Near Yashoda Hospital."

def test_severity_no_landmarks(mock_gemini, mock_geocoding, report_factory):
    mock_geocoding.landmarks.return_value = []
    mock_gemini.set_response('{"severity_score": 3, "severity_reasoning": "No landmarks near."}')
    
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    run_severity_classification(report)
    
    prompt_sent = mock_gemini.severity.call_args[0][1]
    assert "Nearby landmarks within 200m:" not in prompt_sent
    assert report.severity_score == 3

def test_severity_malformed_fallback(mock_gemini, mock_geocoding, report_factory):
    mock_gemini.set_response("Broken JSON Response")
    
    report = report_factory(latitude=17.4245627, longitude=78.4569401)
    run_severity_classification(report)
    
    # Verify fallback scoring and reasoning
    assert report.severity_score == 3
    assert "Fallback severity reasoning due to classification failure" in report.severity_reasoning

def test_severity_null_coordinates(mock_gemini, mock_geocoding, report_factory):
    mock_gemini.set_response('{"severity_score": 3, "severity_reasoning": "No coords."}')
    
    report = report_factory(latitude=None, longitude=None)
    run_severity_classification(report)
    
    mock_geocoding.landmarks.assert_not_called()
    assert report.severity_score == 3
