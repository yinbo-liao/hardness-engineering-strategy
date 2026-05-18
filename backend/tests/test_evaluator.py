import pytest
from backend.app.harness.evaluator import (
    Evaluator,
    EvaluationDimension,
    DimensionResult,
)
from backend.app.harness.tool_registry import (
    ToolRegistry,
    ToolSchema,
    PermissionLevel,
)
from backend.app.harness.planner import TaskNode


class TestDimensionResult:
    def test_defaults(self):
        result = DimensionResult(
            dimension=EvaluationDimension.LINT,
            passed=True,
            score=1.0,
        )
        assert result.dimension == EvaluationDimension.LINT
        assert result.details == {}


class TestEvaluatorWeights:
    @pytest.fixture
    def evaluator(self):
        registry = ToolRegistry()
        return Evaluator(registry)

    def test_weights_sum_to_one(self, evaluator):
        total = sum(evaluator.weights.values())
        assert abs(total - 1.0) < 0.01

    def test_critical_dimensions(self, evaluator):
        critical = {
            EvaluationDimension.UNIT_TESTS,
            EvaluationDimension.SECURITY_SCAN,
            EvaluationDimension.TYPE_CHECK,
        }
        assert critical.issubset(set(evaluator.dimensions))

    def test_thresholds_defined_for_all(self, evaluator):
        for dim in evaluator.dimensions:
            assert dim in evaluator.thresholds


class TestEvaluatorScoring:
    @pytest.fixture
    def registry(self):
        reg = ToolRegistry()

        async def run_tests(**kwargs):
            return {"coverage": 85, "failures": 0, "tests_run": 20}
        async def run_security_scan(**kwargs):
            return {"issues": [], "scanners": ["bandit"]}

        reg.register(
            ToolSchema(name="run_tests", description="", permission_required=PermissionLevel.EXECUTE),
            run_tests,
        )
        reg.register(
            ToolSchema(name="run_security_scan", description="", permission_required=PermissionLevel.EXECUTE),
            run_security_scan,
        )
        return reg

    @pytest.fixture
    def evaluator(self, registry):
        return Evaluator(registry)

    @pytest.mark.asyncio
    async def test_evaluate_passes(self, evaluator):
        task = TaskNode(id="t1", description="test task", task_type="code")
        result = await evaluator.evaluate(task, [], "session-1")
        assert result["passed"] is True
        assert result["weighted_score"] > 0.85
        assert "dimensions" in result
        assert len(result["dimensions"]) == 6

    @pytest.mark.asyncio
    async def test_evaluate_failed_dimensions_not_in_feedback_when_passing(self, evaluator):
        task = TaskNode(id="t2", description="passing task")
        result = await evaluator.evaluate(task, [], "session-2")
        assert result["passed"] is True
        assert result["feedback"] is None

    @pytest.mark.asyncio
    async def test_generate_summary(self, evaluator):
        task = TaskNode(id="t3", description="summary test")
        result = await evaluator.evaluate(task, [], "session-3")
        summary = result["summary"]
        assert "Evaluation:" in summary
        assert "PASS" in summary

    @pytest.mark.asyncio
    async def test_dimensions_all_present(self, evaluator):
        task = TaskNode(id="t4", description="all dims")
        result = await evaluator.evaluate(task, [], "session-4")
        dims = set(result["dimensions"].keys())
        expected = {"unit_tests", "type_check", "lint", "security_scan", "architecture", "performance"}
        assert dims == expected
