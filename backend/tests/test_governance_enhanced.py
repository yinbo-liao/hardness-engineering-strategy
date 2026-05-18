import pytest
from backend.app.harness.governance import Governance


class TestCircularImports:
    @pytest.fixture
    def gov(self):
        return Governance()

    def test_no_import_data(self, gov):
        result = gov._check_circular_imports({"content": "def foo(): pass"})
        assert result["passed"] is True

    def test_clean_imports(self, gov):
        result = gov._check_circular_imports({
            "imports": {
                "a": ["b"],
                "b": ["c"],
                "c": [],
            }
        })
        assert result["passed"] is True

    def test_circular_imports_detected(self, gov):
        result = gov._check_circular_imports({
            "imports": {
                "a": ["b"],
                "b": ["a"],
            }
        })
        assert result["passed"] is False
        assert "Circular imports detected" in result["message"]

    def test_self_referencing_module(self, gov):
        result = gov._check_circular_imports({
            "imports": {
                "x": ["x"],
            }
        })
        assert result["passed"] is False


class TestTestCoverage:
    @pytest.fixture
    def gov(self):
        return Governance()

    def test_no_data_returns_ok(self, gov):
        result = gov._check_test_coverage({"content": "def foo(): pass"})
        assert result["passed"] is True

    def test_test_file_detected(self, gov):
        result = gov._check_test_coverage({
            "content": "def test_foo(): assert True",
        })
        assert result["passed"] is True

    def test_file_path_is_test(self, gov):
        result = gov._check_test_coverage({
            "content": "code without tests",
            "file_path": "tests/test_module.py",
        })
        assert result["passed"] is True

    def test_no_tests_found(self, gov):
        result = gov._check_test_coverage({
            "content": "def add(a, b): return a + b",
            "file_path": "src/utils/helpers.py",
            "test_files": [],
            "test_content": "",
        })
        assert result["passed"] is False
        assert "No test files" in result["message"]
