# Civic Triage Agent - Unit and Integration Tests

This directory contains the automated test suite for the Civic Triage Agent system. All unit and integration tests are designed to run **completely offline**:
- **No Gemini API calls** (mocked in `conftest.py` using `mock_gemini` fixture).
- **No Firestore calls** (mocked in `conftest.py` using `mock_storage` in-memory dictionary).
- **No geocoding/places calls** (mocked in `conftest.py` using `mock_geocoding` geopy/API mocks).

This ensures you can run tests repeatedly during development with zero latency and zero quota usage.

---

## Installation & Running Tests

### 1. Install Testing Dependencies
Ensure testing libraries are installed:
```bash
pip install pytest pytest-mock httpx
```

### 2. Run the Offline Test Suite
To run all tests in this directory, excluding the live geocoding smoke test:
```bash
python -m pytest tests/ -v --ignore=tests/test_mcp_geocoding.py
```

### 3. Run Live Smoke Tests (Quota Consuming / Online)
To run the live Nominatim geocoding check (sparingly, as it hits live APIs):
```bash
python -m pytest tests/test_mcp_geocoding.py -v
```
