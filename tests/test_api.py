"""
API integration tests for Smart-Transit backend.

Run: pytest tests/ -v
"""

import pytest
from backend.app.main import app


@pytest.fixture
def client():
    """Create a synchronous test client."""
    from fastapi.testclient import TestClient
    return TestClient(app)


# --- Health Check ---

def test_health_check_returns_200(client):
    """Health endpoint should always return 200 even without DB."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["version"] == "2.1.0"
    assert data["system"] == "Smart-Transit Backend"
    assert data["database"] in ("connected", "disconnected")
    assert data["ml_model"] in ("loaded", "fallback")


# --- ETA Prediction ---

def test_eta_valid_request(client):
    """ETA endpoint should return 200 (with predictor) or 503 (without)."""
    response = client.get("/eta?distance_meters=5000&current_speed_kmh=30")
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert "prediction" in data
        assert "seconds" in data
        assert "source" in data
        assert data["source"] in ("ML_model", "rule_based_fallback")
        assert data["seconds"] > 0


def test_eta_physics_sanity(client):
    """ETA should be roughly distance/speed for fallback mode."""
    response = client.get("/eta?distance_meters=1000&current_speed_kmh=36")
    if response.status_code == 200:
        data = response.json()
        # 1000m at 36km/h = 1000m at 10m/s = 100s ≈ 1.67 min
        assert abs(data["seconds"] - 100.0) < 10  # Allow some tolerance
    else:
        assert response.status_code == 503  # Predictor not initialized


def test_eta_negative_distance_rejected(client):
    """Negative distance should return 422 validation error."""
    response = client.get("/eta?distance_meters=-100&current_speed_kmh=30")
    assert response.status_code == 422


def test_eta_zero_distance_rejected(client):
    """Zero distance should return 422 (must be > 0)."""
    response = client.get("/eta?distance_meters=0&current_speed_kmh=30")
    assert response.status_code == 422


def test_eta_negative_speed_rejected(client):
    """Negative speed should return 422."""
    response = client.get("/eta?distance_meters=1000&current_speed_kmh=-10")
    assert response.status_code == 422


def test_eta_zero_speed_allowed(client):
    """Zero speed is valid (bus is stopped). Should return 200 or 503."""
    response = client.get("/eta?distance_meters=1000&current_speed_kmh=0")
    assert response.status_code in (200, 503)  # 503 if predictor not initialized


def test_eta_missing_params(client):
    """Missing required params should return 422."""
    response = client.get("/eta")
    assert response.status_code == 422

    response = client.get("/eta?distance_meters=1000")
    assert response.status_code == 422


# --- GPS Ping (Location) ---

def test_location_valid_ping_no_db(client):
    """With valid API key and no DB, posting a GPS ping should return 503."""
    payload = {
        "vehicle_id": "TEST-001",
        "route_id": "RT-101",
        "lat": 31.62,
        "lng": 74.87,
        "speed": 35.0,
    }
    response = client.post("/location", json=payload, headers={"X-API-Key": "sim-key-change-me"})
    # Without DB running, expect 503
    assert response.status_code == 503


def test_location_missing_api_key_rejected(client):
    """GPS ping without API key should be rejected."""
    payload = {
        "vehicle_id": "TEST-001",
        "route_id": "RT-101",
        "lat": 31.62,
        "lng": 74.87,
        "speed": 35.0,
    }
    response = client.post("/location", json=payload)
    assert response.status_code == 403


def test_location_invalid_api_key_rejected(client):
    """GPS ping with invalid API key should be rejected."""
    payload = {
        "vehicle_id": "TEST-001",
        "route_id": "RT-101",
        "lat": 31.62,
        "lng": 74.87,
        "speed": 35.0,
    }
    response = client.post("/location", json=payload, headers={"X-API-Key": "bad-key"})
    assert response.status_code == 403


def test_location_invalid_coordinates(client):
    """Invalid lat/lng should return 422."""
    payload = {
        "vehicle_id": "TEST-001",
        "route_id": "RT-101",
        "lat": 999.0,  # Invalid latitude
        "lng": 74.87,
        "speed": 35.0,
    }
    response = client.post("/location", json=payload, headers={"X-API-Key": "sim-key-change-me"})
    assert response.status_code == 422


def test_location_empty_vehicle_id(client):
    """Empty vehicle_id should return 422."""
    payload = {
        "vehicle_id": "",
        "route_id": "RT-101",
        "lat": 31.62,
        "lng": 74.87,
        "speed": 35.0,
    }
    response = client.post("/location", json=payload, headers={"X-API-Key": "sim-key-change-me"})
    assert response.status_code == 422


# --- Live Buses ---

def test_live_buses_no_db(client):
    """Without DB, live buses endpoint should return 503."""
    response = client.get("/buses/live")
    assert response.status_code == 503


# --- Routes ---

def test_routes_no_db(client):
    """Without DB, routes endpoint should return 503."""
    response = client.get("/routes")
    assert response.status_code == 503


# --- Stats ---

def test_stats_no_db(client):
    """Stats endpoint with valid JWT should return 503 when DB is unavailable."""
    auth = client.post("/auth/token", json={"username": "admin", "password": "admin123"})
    assert auth.status_code == 200
    token = auth.json()["access_token"]
    response = client.get("/stats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503


def test_stats_requires_auth(client):
    """Stats endpoint should require bearer authentication."""
    response = client.get("/stats")
    assert response.status_code == 401


# --- Auth ---

def test_auth_token_success(client):
    """Auth endpoint should issue JWT for valid credentials."""
    response = client.post("/auth/token", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_token_invalid_credentials(client):
    """Auth endpoint should reject invalid credentials."""
    response = client.post("/auth/token", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


# --- OpenAPI Schema ---

def test_openapi_schema_available(client):
    """OpenAPI schema should be accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Smart-Transit API Gateway"
    assert "/eta" in schema["paths"]
    assert "/location" in schema["paths"]
    assert "/buses/live" in schema["paths"]
