import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_triage_no_key(mocker, monkeypatch, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    mock_process = mocker.patch("main.process_report")
    
    response = client.post("/triage", data={"raw_text": "Pothole on Main St."})
    
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}
    mock_process.assert_not_called()

def test_triage_wrong_key(mocker, monkeypatch, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    mock_process = mocker.patch("main.process_report")
    
    response = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "wrong-secret-key"}
    )
    
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}
    mock_process.assert_not_called()

def test_triage_correct_key(mocker, monkeypatch, report_factory, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    mock_process = mocker.patch("main.process_report")
    mock_process.return_value = report_factory(issue_type="pothole", description="Mock pothole")
    
    response = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    
    assert response.status_code == 200
    assert response.json()["issue_type"] == "pothole"
    assert response.json()["description"] == "Mock pothole"
    mock_process.assert_called_once()

def test_health_check_no_auth(monkeypatch, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    
    response = client.get("/")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_triage_not_configured(mocker, monkeypatch, client):
    monkeypatch.delenv("TRIAGE_API_KEY", raising=False)
    monkeypatch.delenv("TRIAGE_DEMO_API_KEY", raising=False)
    mock_process = mocker.patch("main.process_report")
    
    response = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    
    assert response.status_code == 500
    assert "TRIAGE_API_KEY environment variable is not configured" in response.json()["detail"]
    mock_process.assert_not_called()

def test_triage_demo_key_success(mocker, monkeypatch, report_factory, client):
    monkeypatch.delenv("TRIAGE_API_KEY", raising=False)
    monkeypatch.setenv("TRIAGE_DEMO_API_KEY", "demo-secret-key")
    mock_process = mocker.patch("main.process_report")
    mock_process.return_value = report_factory(issue_type="pothole", description="Mock pothole")
    
    response = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "demo-secret-key"}
    )
    
    assert response.status_code == 200
    assert response.json()["issue_type"] == "pothole"
    mock_process.assert_called_once()

def test_resolve_no_key(monkeypatch, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "admin-secret-key")
    response = client.patch("/reports/some-id/resolve")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing Admin API key"}

def test_resolve_demo_key_rejected(monkeypatch, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "admin-secret-key")
    monkeypatch.setenv("TRIAGE_DEMO_API_KEY", "demo-secret-key")
    response = client.patch(
        "/reports/some-id/resolve",
        headers={"X-API-Key": "demo-secret-key"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing Admin API key"}

def test_resolve_admin_key_success(mocker, monkeypatch, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "admin-secret-key")
    mock_db = mocker.patch("agents.storage.db")
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"report_id": "some-id"}]
    
    response = client.patch(
        "/reports/some-id/resolve",
        headers={"X-API-Key": "admin-secret-key"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Report some-id marked as resolved."
    }
    # Verify update was called
    mock_db.table.assert_any_call("reports")
    mock_db.table.return_value.update.assert_called_once_with({"status": "resolved"})

def test_resolve_admin_key_not_found(mocker, monkeypatch, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "admin-secret-key")
    mock_db = mocker.patch("agents.storage.db")
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    response = client.patch(
        "/reports/some-id/resolve",
        headers={"X-API-Key": "admin-secret-key"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Report not found"}

def test_resolve_not_configured(monkeypatch, client):
    monkeypatch.delenv("TRIAGE_API_KEY", raising=False)
    response = client.patch(
        "/reports/some-id/resolve",
        headers={"X-API-Key": "admin-secret-key"}
    )
    assert response.status_code == 500
    assert "TRIAGE_API_KEY environment variable is not configured" in response.json()["detail"]


