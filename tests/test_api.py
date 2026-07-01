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
    response = client.get("/health")
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


# ─────────────────────────────────────────────────────────────────────────────
# Telemetry Endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_telemetry_requires_api_key(client):
    """Telemetry endpoint must reject requests without API key."""
    response = client.post("/location/telemetry", json={"vehicle_id": "BUS-01", "passenger_count": 12})
    assert response.status_code == 403


def test_telemetry_invalid_api_key(client):
    """Telemetry endpoint must reject invalid API key."""
    response = client.post(
        "/location/telemetry",
        json={"vehicle_id": "BUS-01", "passenger_count": 12},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_telemetry_negative_count_rejected(client):
    """Negative passenger count must be rejected."""
    response = client.post(
        "/location/telemetry",
        json={"vehicle_id": "BUS-01", "passenger_count": -1},
        headers={"X-API-Key": "sim-key-change-me"},
    )
    assert response.status_code == 422


def test_telemetry_empty_vehicle_id_rejected(client):
    """Empty vehicle_id must be rejected."""
    response = client.post(
        "/location/telemetry",
        json={"vehicle_id": "", "passenger_count": 5},
        headers={"X-API-Key": "sim-key-change-me"},
    )
    assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Admin Endpoints (JWT protected)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_token(client):
    """Get a valid JWT token for admin tests."""
    res = client.post("/auth/token", json={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_admin_routes_requires_auth(client):
    """Admin routes list should reject unauthenticated requests."""
    response = client.get("/admin/routes")
    assert response.status_code == 401


def test_admin_routes_with_auth_no_db(client, auth_token):
    """Admin routes with valid JWT but no DB should return 503."""
    response = client.get("/admin/routes", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 503


def test_admin_create_route_validation(client, auth_token):
    """Admin route creation with missing stops should return 422."""
    payload = {"route_id": "RT-TEST", "route_name": "Test Route", "stops": []}
    response = client.post(
        "/admin/routes",
        json=payload,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    # Either 422 validation or 503 no-DB, both are acceptable
    assert response.status_code in (422, 503)


def test_admin_gtfs_status_requires_auth(client):
    """GTFS status endpoint should require auth."""
    response = client.get("/admin/gtfs/status")
    assert response.status_code == 401


def test_admin_gtfs_status_with_auth_no_db(client, auth_token):
    """GTFS status with valid JWT but no DB returns 503."""
    response = client.get("/admin/gtfs/status", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 503


# ─────────────────────────────────────────────────────────────────────────────
# GTFS Pipeline Unit Tests (no DB required)
# ─────────────────────────────────────────────────────────────────────────────

def test_gtfs_demo_feed_generates_routes():
    """Demo GTFS feed should parse into at least 2 routes."""
    from scripts.gtfs_ingest import generate_demo_gtfs, transform_gtfs
    gtfs = generate_demo_gtfs()
    routes = transform_gtfs(gtfs)
    assert len(routes) >= 2


def test_gtfs_routes_have_required_fields():
    """Each parsed GTFS route must have route_id, route_name, and stops."""
    from scripts.gtfs_ingest import generate_demo_gtfs, transform_gtfs
    routes = transform_gtfs(generate_demo_gtfs())
    for route in routes:
        assert "route_id" in route
        assert "route_name" in route
        assert "stops" in route
        assert len(route["stops"]) >= 2


def test_gtfs_stops_have_valid_coordinates():
    """Each stop must have valid lat/lng values."""
    from scripts.gtfs_ingest import generate_demo_gtfs, transform_gtfs
    routes = transform_gtfs(generate_demo_gtfs())
    for route in routes:
        for stop in route["stops"]:
            assert -90 <= stop["lat"] <= 90
            assert -180 <= stop["lng"] <= 180
            assert isinstance(stop["stop_name"], str)
            assert len(stop["stop_name"]) > 0


def test_gtfs_stop_sequences_are_ordered():
    """Stop sequences must be in ascending order."""
    from scripts.gtfs_ingest import generate_demo_gtfs, transform_gtfs
    routes = transform_gtfs(generate_demo_gtfs())
    for route in routes:
        seqs = [s["sequence"] for s in route["stops"]]
        assert seqs == sorted(seqs), f"Stops not ordered in route {route['route_id']}"
