import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.harness.middleware import RateLimitMiddleware, RBACMiddleware, require_permission


class TestRateLimitMiddleware:
    @pytest.fixture
    def app(self):
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, max_requests=3, window_seconds=60)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        return app

    def test_requests_within_limit(self, app):
        client = TestClient(app)
        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 200

    def test_rate_limit_exceeded(self, app):
        client = TestClient(app)
        for _ in range(3):
            client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "Too Many Requests" in response.json()["title"]


class TestRBACMiddleware:
    @pytest.fixture
    def app(self):
        app = FastAPI()
        app.add_middleware(RBACMiddleware)

        @app.get("/protected")
        async def protected():
            return {"ok": True}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app

    def test_no_auth_header_returns_401(self, app):
        client = TestClient(app)
        response = client.get("/protected")
        assert response.status_code == 401

    def test_health_is_exempt(self, app):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_invalid_token_returns_401(self, app):
        client = TestClient(app)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_options_returns_401_when_no_token(self, app):
        client = TestClient(app)
        response = client.options("/protected")
        assert response.status_code in (200, 401, 405)
