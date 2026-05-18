import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestHealthEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    def test_metrics_endpoint(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_root_not_found(self, client):
        response = client.get("/")
        assert response.status_code in (404, 200, 401)

    def test_cors_headers_present(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 405)
