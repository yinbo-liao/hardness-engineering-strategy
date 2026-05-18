import pytest
from backend.app.harness.context_manager import ContextManager, ContextBudget


class TestContextBudget:
    def test_defaults(self):
        b = ContextBudget()
        assert b.total_max == 8000
        assert b.global_max == 2000
        assert b.task_max == 1500
        assert b.retrieved_max == 3000
        assert b.memory_max == 1500


class TestScopeDetection:
    def test_api_scope(self):
        cm = ContextManager()
        assert cm._determine_scope("create a new FastAPI endpoint for users") == "api"
        assert cm._determine_scope("add a REST handler for login") == "api"

    def test_ui_scope(self):
        cm = ContextManager()
        assert cm._determine_scope("build a React component for the dashboard") == "ui"
        assert cm._determine_scope("fix CSS on the login page") == "ui"

    def test_db_scope(self):
        cm = ContextManager()
        assert cm._determine_scope("add migration for the users table") == "db"
        assert cm._determine_scope("create SQLAlchemy model for orders") == "db"

    def test_infra_scope(self):
        cm = ContextManager()
        assert cm._determine_scope("update Docker deploy config") == "infra"

    def test_test_scope(self):
        cm = ContextManager()
        assert cm._determine_scope("write pytest coverage for the API") == "test"

    def test_security_scope(self):
        cm = ContextManager()
        assert cm._determine_scope("implement OAuth JWT authentication") == "security"

    def test_fallback_general(self):
        cm = ContextManager()
        assert cm._determine_scope("do something vague") == "general"


class TestContextAssembly:
    def test_build_context_structure(self):
        cm = ContextManager()
        ctx = cm.build_context("add a FastAPI endpoint /users")

        assert ctx["version"] == "harness_context_v2"
        assert ctx["scope"] == "api"
        assert "layers" in ctx
        assert "budget" in ctx
        assert "global" in ctx["layers"]
        assert "task" in ctx["layers"]
        assert "retrieved" in ctx["layers"]
        assert "memory" in ctx["layers"]

    def test_budget_tracking(self):
        cm = ContextManager()
        ctx = cm.build_context("build a React dashboard component")

        assert ctx["budget"]["allocated"] > 0
        assert ctx["budget"]["remaining"] > 0
        assert (
            ctx["budget"]["allocated"] + ctx["budget"]["remaining"]
            == ctx["budget"]["total_max"]
        )

    def test_global_context_priority(self):
        cm = ContextManager()
        ctx = cm.build_context("add a FastAPI endpoint")
        assert ctx["layers"]["global"]["priority"] == "critical"

    def test_scope_filtering_api(self):
        cm = ContextManager()
        ctx = cm.build_context("create an API route for products", task_scope="api")

        global_content = ctx["layers"]["global"]["content"]
        coding = global_content.get("coding_standards", {})
        assert "python" in coding
        assert "typescript" not in coding

        api_conventions = global_content.get("api_conventions", {})
        assert "rest" in api_conventions

    def test_extracted_constraints(self):
        cm = ContextManager()
        ctx = cm.build_context("build an async API endpoint with tests")

        constraints = ctx["layers"]["task"]["content"]["constraints"]
        assert "Must use async/await pattern" in constraints
        assert "Must include unit tests" in constraints
        assert "Must follow OpenAPI schema" in constraints


class TestContextWithoutVectorDB:
    def test_retrieved_empty_without_db(self):
        cm = ContextManager(vector_db_client=None)
        ctx = cm.build_context("anything")
        assert ctx["layers"]["retrieved"]["content"] == []
        assert ctx["layers"]["retrieved"]["token_estimate"] == 0

    def test_memory_empty_without_db(self):
        cm = ContextManager(vector_db_client=None)
        ctx = cm.build_context("anything")
        assert ctx["layers"]["memory"]["content"] == []
        assert ctx["layers"]["memory"]["token_estimate"] == 0
