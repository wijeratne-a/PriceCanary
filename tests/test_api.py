"""Tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from src.api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "PriceCanary"


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_ingest_endpoint_valid(client):
    """Test ingest endpoint with valid data"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "sku": "SKU-001",
        "price": 99.99,
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    response = client.post("/api/v1/ingest", json=record)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "alerts_created" in data


def test_ingest_endpoint_invalid(client):
    """Test ingest endpoint with invalid data"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "sku": "SKU-001",
        "price": -10.0,  # Invalid price
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5
    }
    
    response = client.post("/api/v1/ingest", json=record)
    # Should either return 200 with violations or 422 for validation error
    assert response.status_code in [200, 422]


def test_alerts_endpoint(client):
    """Test alerts endpoint"""
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total" in data


def test_alerts_endpoint_filtered(client):
    """Test alerts endpoint with filters"""
    response = client.get("/api/v1/alerts?severity=critical&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data


def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    # Should return Prometheus format
    assert "text/plain" in response.headers.get("content-type", "")


def test_acknowledge_alert(client):
    """Test acknowledge alert endpoint"""
    # First create an alert by ingesting problematic data
    record = {
        "timestamp": datetime.now().isoformat(),
        "sku": "SKU-001",
        "price": 50000.0,  # Likely to trigger violation
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    client.post("/api/v1/ingest", json=record)
    
    # Get alerts
    response = client.get("/api/v1/alerts")
    alerts = response.json().get("alerts", [])
    
    if alerts:
        alert_id = alerts[0]["alert_id"]
        response = client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
        assert response.status_code == 200


def test_resolve_alert(client):
    """Test resolve alert endpoint"""
    # Get alerts
    response = client.get("/api/v1/alerts")
    alerts = response.json().get("alerts", [])
    
    if alerts:
        alert_id = alerts[0]["alert_id"]
        response = client.post(f"/api/v1/alerts/{alert_id}/resolve")
        # Should succeed or return 404 if alert doesn't exist
        assert response.status_code in [200, 404]

