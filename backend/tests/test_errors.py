import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.harness.errors import (
    problem_detail,
    validation_error,
    not_found,
    conflict,
    too_many_requests,
    unauthorized,
    forbidden,
    internal_error,
)


class TestProblemDetail:
    @pytest.fixture
    def app(self):
        from fastapi import Request as FastAPIRequest
        app = FastAPI()

        @app.get("/bad-request")
        async def bad_request(request: FastAPIRequest):
            return validation_error(request, "Invalid input")

        @app.get("/not-found")
        async def not_found_endpoint(request: FastAPIRequest):
            return not_found(request, "Task", "task-123")

        @app.get("/conflict")
        async def conflict_endpoint(request: FastAPIRequest):
            return conflict(request, "Task already exists")

        @app.get("/unauthorized")
        async def unauthorized_endpoint(request: FastAPIRequest):
            return unauthorized(request, "Token expired")

        @app.get("/forbidden")
        async def forbidden_endpoint(request: FastAPIRequest):
            return forbidden(request, "Requires ADMIN permission")

        return app

    def test_validation_error_format(self, app):
        client = TestClient(app)
        response = client.get("/bad-request")
        assert response.status_code == 400
        body = response.json()
        assert body["type"].startswith("https://")
        assert body["title"] == "Validation Error"
        assert body["status"] == 400

    def test_not_found_format(self, app):
        client = TestClient(app)
        response = client.get("/not-found")
        assert response.status_code == 404
        body = response.json()
        assert body["title"] == "Not Found"
        assert "Task" in body["detail"]

    def test_conflict_format(self, app):
        client = TestClient(app)
        response = client.get("/conflict")
        assert response.status_code == 409
        body = response.json()
        assert body["title"] == "Conflict"

    def test_unauthorized_format(self, app):
        client = TestClient(app)
        response = client.get("/unauthorized")
        assert response.status_code == 401
        body = response.json()
        assert body["title"] == "Unauthorized"

    def test_forbidden_format(self, app):
        client = TestClient(app)
        response = client.get("/forbidden")
        assert response.status_code == 403
        body = response.json()
        assert body["title"] == "Forbidden"

    def test_all_responses_include_instance(self, app):
        client = TestClient(app)
        for path in ["/bad-request", "/not-found", "/conflict"]:
            response = client.get(path)
            assert "instance" in response.json()
