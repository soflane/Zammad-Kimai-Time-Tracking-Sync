import pytest
from fastapi.testclient import TestClient

from app.main import app

def test_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Zammad-Kimai Time Tracking Sync API"

def test_login(client: TestClient):
    form_data = {
        "username": "admin",
        "password": "changeme"
    }
    response = client.post("/token", data=form_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
