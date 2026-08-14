import pytest
from agents.dispatch_agent import run_dispatch

def test_dispatch_success(mock_gemini, report_factory):
    report = report_factory(issue_type="pothole", severity_score=4, severity_reasoning="Large hazard.")
    mock_gemini.set_response('{"department": "Roads & Transport Department", "work_order_text": "WORK ORDER CONTENT"}')
    
    run_dispatch(report)
    
    assert report.department == "Roads & Transport Department"
    assert report.work_order_text == "WORK ORDER CONTENT"

def test_dispatch_fallback(mock_gemini, report_factory):
    report = report_factory(
        issue_type="pothole", 
        severity_score=4, 
        severity_reasoning="Large hazard.", 
        address="Main St", 
        report_id="match-id"
    )
    mock_gemini.set_response("Broken JSON Response")
    
    run_dispatch(report)
    
    # Assert fallback template properties
    assert report.department == "General Complaints Department"
    assert "WORK ORDER — match-id (AUTO-FALLBACK, NEEDS MANUAL REVIEW)" in report.work_order_text
    assert "Issue: pothole" in report.work_order_text
    assert "Location: Main St" in report.work_order_text
    assert "Severity: 4/5 — Large hazard." in report.work_order_text
    assert "Assigned department: General Complaints Department" in report.work_order_text
