import pytest
from agents.intake_agent import run_intake

def test_run_intake_text_only(mock_gemini, mock_geocoding):
    # Mock model response for structured extraction
    mock_gemini.set_response('{"issue_type": "pothole", "description": "Large pothole.", "address_or_landmark": "Main Street"}')
    
    report = run_intake(raw_text="Huge pothole on Main Street.")
    
    assert report.issue_type == "pothole"
    assert report.description == "Large pothole."
    assert report.address == "Main Street"
    assert report.latitude == 17.4245627
    assert report.longitude == 78.4569401
    mock_gemini.intake.assert_called_once()

def test_pii_redaction_before_model_call(mock_gemini, mock_geocoding):
    mock_gemini.set_response('{"issue_type": "pothole", "description": "redacted info", "address_or_landmark": "Main St"}')
    
    run_intake(raw_text="Call me at 123-456-7890 or email test@example.com.")
    
    # Assert on what the mock was actually called with, verifying it was redacted BEFORE the model call
    prompt_sent = mock_gemini.intake.call_args[0][1]
    assert "123-456-7890" not in prompt_sent
    assert "test@example.com" not in prompt_sent
    assert "[redacted]" in prompt_sent

def test_malformed_json_fallback(mock_gemini, mock_geocoding):
    # Model returns broken JSON
    mock_gemini.set_response("Broken JSON Response")
    
    report = run_intake(raw_text="Pothole near library.")
    
    # Safe text fallback logic
    assert report.description == "Pothole near library."

def test_geocoding_called_with_address(mock_gemini, mock_geocoding):
    mock_gemini.set_response('{"issue_type": "pothole", "description": "Pothole", "address_or_landmark": "Charminar"}')
    mock_geocoding.geocode.return_value = {"latitude": 17.3616, "longitude": 78.4746, "resolved_address": "Charminar, Hyderabad"}
    
    report = run_intake(raw_text="Pothole at Charminar.")
    
    mock_geocoding.geocode.assert_called_once_with("Charminar")
    assert report.latitude == 17.3616
    assert report.longitude == 78.4746

def test_multimodal_called_when_image_present(mock_gemini, mock_geocoding):
    mock_gemini.set_response('{"issue_type": "pothole", "description": "Pothole in image", "address_or_landmark": "Main Street"}')
    
    run_intake(raw_text="Pothole", image_filename="photo.jpg", image_bytes=b"fake-bytes", image_mime_type="image/jpeg")
    
    mock_gemini.intake.assert_not_called()
    mock_gemini.intake_multi.assert_called_once()
