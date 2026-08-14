import pytest

def test_orchestrator_happy_path(mocker, mock_storage, report_factory):
    # Mock each agent function at orchestrator level
    mock_intake = mocker.patch("orchestrator.run_intake")
    mock_dup = mocker.patch("orchestrator.run_duplicate_check")
    mock_sev = mocker.patch("orchestrator.run_severity_classification")
    mock_dispatch = mocker.patch("orchestrator.run_dispatch")
    
    r_intake = report_factory(is_duplicate=False)
    r_dup = report_factory(is_duplicate=False)
    r_sev = report_factory(is_duplicate=False)
    r_dispatch = report_factory(is_duplicate=False, department="Roads & Transport Department", work_order_text="DRAFT WORK ORDER")
    
    mock_intake.return_value = r_intake
    mock_dup.return_value = r_dup
    mock_sev.return_value = r_sev
    mock_dispatch.return_value = r_dispatch
    
    from orchestrator import process_report
    res = process_report(raw_text="A pothole.")
    
    # Confirm execution order
    mock_intake.assert_called_once()
    mock_dup.assert_called_once()
    mock_sev.assert_called_once()
    mock_dispatch.assert_called_once()
    
    # Confirm result and persistent save call
    assert res.department == "Roads & Transport Department"
    mock_storage.save.assert_called_once_with(r_dispatch)

def test_orchestrator_duplicate_short_circuit(mocker, mock_storage, report_factory):
    mock_intake = mocker.patch("orchestrator.run_intake")
    mock_dup = mocker.patch("orchestrator.run_duplicate_check")
    mock_sev = mocker.patch("orchestrator.run_severity_classification")
    mock_dispatch = mocker.patch("orchestrator.run_dispatch")
    
    r_intake = report_factory(is_duplicate=False)
    r_dup = report_factory(is_duplicate=True, duplicate_of_report_id="first-report-id")
    
    mock_intake.return_value = r_intake
    mock_dup.return_value = r_dup
    
    from orchestrator import process_report
    res = process_report(raw_text="Duplicate pothole report.")
    
    # Confirm early return branch logic: severity and dispatch bypassed
    mock_intake.assert_called_once()
    mock_dup.assert_called_once()
    mock_sev.assert_not_called()
    mock_dispatch.assert_not_called()
    
    # Verify save_report is still executed on early return
    assert res.is_duplicate is True
    assert res.duplicate_of_report_id == "first-report-id"
    mock_storage.save.assert_called_once_with(r_dup)

def test_orchestrator_calls_get_all_reports_first(mocker, mock_storage, report_factory):
    mock_intake = mocker.patch("orchestrator.run_intake")
    mock_dup = mocker.patch("orchestrator.run_duplicate_check")
    mocker.patch("orchestrator.run_severity_classification")
    mocker.patch("orchestrator.run_dispatch")
    
    r_intake = report_factory()
    mock_intake.return_value = r_intake
    mock_dup.return_value = r_intake
    
    from orchestrator import process_report
    process_report(raw_text="A pothole.")
    
    # Verify database fetch is called at the start of every pipeline invocation
    mock_storage.get_all.assert_called_once()
