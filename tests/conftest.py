import pytest
from agents.schema import Report

@pytest.fixture
def mock_gemini(mocker):
    """
    Mock runner_utils.run_agent and run_agent_multimodal in the namespaces
    where they are actually imported and used by each agent.
    """
    mock_intake_run = mocker.patch("agents.intake_agent.run_agent")
    mock_intake_multi = mocker.patch("agents.intake_agent.run_agent_multimodal")
    mock_dup_run = mocker.patch("agents.duplicate_check_agent.run_agent")
    mock_sev_run = mocker.patch("agents.severity_classifier_agent.run_agent")
    mock_dispatch_run = mocker.patch("agents.dispatch_agent.run_agent")
    
    class GeminiMocks:
        def __init__(self):
            self.intake = mock_intake_run
            self.intake_multi = mock_intake_multi
            self.duplicate = mock_dup_run
            self.severity = mock_sev_run
            self.dispatch = mock_dispatch_run
            
        def set_response(self, text):
            self.intake.return_value = text
            self.intake_multi.return_value = text
            self.duplicate.return_value = text
            self.severity.return_value = text
            self.dispatch.return_value = text
                
        def set_side_effect(self, side_effect):
            self.intake.side_effect = side_effect
            self.intake_multi.side_effect = side_effect
            self.duplicate.side_effect = side_effect
            self.severity.side_effect = side_effect
            self.dispatch.side_effect = side_effect

    return GeminiMocks()

@pytest.fixture
def mock_geocoding(mocker):
    """
    Mock geocoding server function imports in the namespaces where they are used.
    """
    mock_geocode = mocker.patch("agents.intake_agent.geocode_address_core")
    mock_distance = mocker.patch("agents.duplicate_check_agent.distance_meters_core")
    mock_landmarks = mocker.patch("agents.severity_classifier_agent.nearby_landmarks_core")
    
    # Set default behaviors
    mock_geocode.return_value = {"latitude": 17.4245627, "longitude": 78.4569401, "resolved_address": "Mock Address"}
    mock_distance.return_value = 10.0
    mock_landmarks.return_value = []
    
    class GeocodingMocks:
        def __init__(self, geocode, distance, landmarks):
            self.geocode = geocode
            self.distance = distance
            self.landmarks = landmarks
            
    return GeocodingMocks(mock_geocode, mock_distance, mock_landmarks)

@pytest.fixture
def mock_storage(mocker):
    """
    Mock storage save/get imports at the orchestrator level.
    """
    in_memory_db = {}
    
    def fake_save(report):
        if not report.report_id:
            return
        in_memory_db[report.report_id] = report
        
    def fake_get_all():
        return list(in_memory_db.values())
        
    mock_save = mocker.patch("orchestrator.save_report", side_effect=fake_save)
    mock_get_all = mocker.patch("orchestrator.get_all_reports", side_effect=fake_get_all)
    
    class StorageMocks:
        def __init__(self, save, get_all, db):
            self.save = save
            self.get_all = get_all
            self.db = db
            
        def clear(self):
            self.db.clear()
            
    return StorageMocks(mock_save, mock_get_all, in_memory_db)

@pytest.fixture
def report_factory():
    """
    Factory fixture to build Report instances with sensible defaults.
    """
    def _create_report(**kwargs):
        defaults = {
            "raw_text": "Sample citizen report text",
            "image_filename": None,
            "issue_type": "pothole",
            "description": "A description of the issue.",
            "latitude": 17.4245627,
            "longitude": 78.4569401,
            "address": "Yashoda Hospital, Somajiguda, Hyderabad",
            "is_duplicate": False,
            "duplicate_of_report_id": None,
            "severity_score": 3,
            "severity_reasoning": "Standard severity reasoning.",
            "department": "Roads & Transport Department",
            "work_order_text": "Standard work order text",
            "report_id": "test-report-id-12345"
        }
        defaults.update(kwargs)
        return Report(**defaults)
    return _create_report
