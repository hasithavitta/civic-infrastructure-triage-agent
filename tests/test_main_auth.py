import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def reset_limiter():
    from main import reset_rate_limiter
    reset_rate_limiter()

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

def test_triage_rate_limiting(mocker, monkeypatch, report_factory, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    mock_process = mocker.patch("main.process_report")
    mock_process.return_value = report_factory(issue_type="pothole", description="Mock pothole")
    
    # 5 successful requests from the same IP should pass
    for i in range(5):
        response = client.post(
            "/triage", 
            data={"raw_text": "Pothole on Main St."}, 
            headers={"X-API-Key": "test-secret-key"}
        )
        assert response.status_code == 200, f"Request {i+1} failed"
    
    # 6th request should fail with 429
    response_6 = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    assert response_6.status_code == 429
    assert response_6.json() == {"detail": "Rate limit exceeded. Please try again later."}
    assert "Retry-After" in response_6.headers
    retry_after = int(response_6.headers["Retry-After"])
    assert 50 <= retry_after <= 60

    # Confirm process_report was called exactly 5 times
    assert mock_process.call_count == 5

def test_triage_rate_limiting_400_does_not_consume_slot(mocker, monkeypatch, report_factory, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    mock_process = mocker.patch("main.process_report")
    mock_process.return_value = report_factory(issue_type="pothole")
    
    # Send a request with no content (400 validation error)
    response_400 = client.post(
        "/triage", 
        data={}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    assert response_400.status_code == 400
    
    # We should still be able to make 5 successful requests
    for i in range(5):
        response = client.post(
            "/triage", 
            data={"raw_text": "Pothole on Main St."}, 
            headers={"X-API-Key": "test-secret-key"}
        )
        assert response.status_code == 200
        
    # The 6th valid request should be rate-limited
    response_limit = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    assert response_limit.status_code == 429

def test_triage_rate_limiting_401_does_not_consume_slot(mocker, monkeypatch, report_factory, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    mock_process = mocker.patch("main.process_report")
    mock_process.return_value = report_factory(issue_type="pothole")
    
    # Send a request with a wrong key (401 validation error)
    response_401 = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "wrong-key"}
    )
    assert response_401.status_code == 401
    
    # We should still be able to make 5 successful requests
    for i in range(5):
        response = client.post(
            "/triage", 
            data={"raw_text": "Pothole on Main St."}, 
            headers={"X-API-Key": "test-secret-key"}
        )
        assert response.status_code == 200
        
    # The 6th valid request should be rate-limited
    response_limit = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    assert response_limit.status_code == 429

def test_triage_rate_limiting_time_decay(mocker, monkeypatch, report_factory, client):
    monkeypatch.setenv("TRIAGE_API_KEY", "test-secret-key")
    mock_process = mocker.patch("main.process_report")
    mock_process.return_value = report_factory(issue_type="pothole")
    
    mock_time = mocker.patch("time.monotonic")
    mock_time.return_value = 100.0
    
    # Make 5 requests at time=100.0
    for i in range(5):
        response = client.post(
            "/triage", 
            data={"raw_text": "Pothole on Main St."}, 
            headers={"X-API-Key": "test-secret-key"}
        )
        assert response.status_code == 200
        
    # 6th request at time=100.0 gets rate-limited
    response_limit = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    assert response_limit.status_code == 429
    
    # Advance time by 61 seconds (time=161.0)
    mock_time.return_value = 161.0
    
    # We should now be able to request successfully again
    response_after = client.post(
        "/triage", 
        data={"raw_text": "Pothole on Main St."}, 
        headers={"X-API-Key": "test-secret-key"}
    )
    assert response_after.status_code == 200


