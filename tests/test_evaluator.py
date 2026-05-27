import pytest
from hardness_plugin.evaluator import (
    evaluate_code_quality,
    EvaluationDimension,
    DimensionResult,
    WEIGHTS,
)


class TestDimensionResult:
    def test_defaults(self):
        result = DimensionResult(
            dimension=EvaluationDimension.LINT,
            passed=True,
            score=1.0,
        )
        assert result.dimension == EvaluationDimension.LINT
        assert result.details == {}
        assert result.logs == []


class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_all_dimensions_have_weights(self):
        for dim in EvaluationDimension:
            assert dim in WEIGHTS


class TestEvaluateCodeQuality:
    def test_clean_code_passes(self):
        content = (
            '"""Module docstring."""\n'
            'from typing import List, Optional\n\n'
            'def greet(name: str) -> str:\n'
            '    """Return greeting."""\n'
            '    return f"Hello, {name}"\n\n'
            'def test_greet():\n'
            '    assert greet("world") == "Hello, world"\n'
        )
        result = evaluate_code_quality("src/module.py", content)
        assert result["passed"] is True
        assert result["weighted_score"] > 0.8

    def test_secret_detection_fails(self):
        content = 'password = "my-secret-password-123"\napi_key = "sk-abc123def456"'
        result = evaluate_code_quality("config.py", content)
        dims = result["dimensions"]
        assert dims["security_scan"]["passed"] is False
        assert dims["security_scan"]["score"] == 0.0

    def test_sql_injection_detected(self):
        content = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
        result = evaluate_code_quality("db.py", content)
        assert result["dimensions"]["security_scan"]["passed"] is False

    def test_eval_detected(self):
        content = 'result = eval(user_input)'
        result = evaluate_code_quality("dangerous.py", content)
        assert result["dimensions"]["security_scan"]["passed"] is False

    def test_no_type_hints_flags(self):
        content = 'def add(a, b):\n    return a + b\n'
        result = evaluate_code_quality("math.py", content)
        assert result["dimensions"]["type_check"]["passed"] is False

    def test_type_hints_pass(self):
        content = 'from typing import Optional\ndef add(a: int, b: int) -> int:\n    return a + b\n'
        result = evaluate_code_quality("math.py", content)
        assert result["dimensions"]["type_check"]["passed"] is True

    def test_test_file_gets_higher_score(self):
        content = 'def test_something():\n    assert True\n'
        result = evaluate_code_quality("tests/test_stuff.py", content)
        assert result["dimensions"]["unit_tests"]["score"] > 0.8

    def test_tabs_detected(self):
        content = "def foo():\n\treturn 1\n"
        result = evaluate_code_quality("tabs.py", content)
        assert result["dimensions"]["lint"]["passed"] is False

    def test_all_six_dimensions_present(self):
        result = evaluate_code_quality("empty.py", "")
        dims = set(result["dimensions"].keys())
        expected = {"unit_tests", "type_check", "lint", "security_scan", "architecture", "performance"}
        assert dims == expected

    def test_return_shape(self):
        result = evaluate_code_quality("test.py", "x = 1")
        assert "file" in result
        assert "passed" in result
        assert "weighted_score" in result
        assert "dimensions" in result
        assert "issues" in result
        assert result["file"] == "test.py"
