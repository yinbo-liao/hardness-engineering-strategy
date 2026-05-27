import pytest
from hardness_plugin.token_optimizer import TokenOptimizer, TokenStats


class TestTokenOptimizer:
    @pytest.fixture
    def optimizer(self):
        return TokenOptimizer(max_tokens=8000)

    def test_default_budgets_sum_to_max(self, optimizer):
        total = sum(optimizer.budgets.values())
        assert abs(total - 8000) < 100

    def test_estimate_tokens(self, optimizer):
        assert optimizer.estimate_tokens("hello world") == 2
        assert optimizer.estimate_tokens("") == 1
        long_text = "x" * 400
        assert optimizer.estimate_tokens(long_text) == 100

    def test_truncate_to_budget_short_content(self, optimizer):
        content = "short"
        result = optimizer.truncate_to_budget(content, 100)
        assert result == content

    def test_truncate_to_budget_long_content(self, optimizer):
        content = "x" * 10000
        result = optimizer.truncate_to_budget(content, 100)
        assert len(result) < len(content)
        assert "... [truncated] ..." in result

    def test_compress_redundant_removes_dup_blank_lines(self, optimizer):
        content = "line1\n\n\n\nline2"
        result = optimizer.compress_redundant(content)
        lines = result.split("\n")
        assert len(lines) < 5

    def test_compress_redundant_removes_comments(self, optimizer):
        content = "# comment 1\ncode1\n// comment 2\ncode2"
        result = optimizer.compress_redundant(content)
        assert "# comment 1" not in result
        assert "// comment 2" not in result
        assert "code1" in result
        assert "code2" in result

    def test_compress_redundant_removes_dup_imports(self, optimizer):
        content = "from typing import List\nfrom typing import List\ncode"
        result = optimizer.compress_redundant(content)
        imports = [l for l in result.split("\n") if "from typing" in l]
        assert len(imports) == 1

    def test_optimize_context_balanced(self, optimizer):
        layers = {
            "global": {"content": {"rules": "test rules"}},
            "task": {"content": {"desc": "a task"}},
            "retrieved": {"content": [{"file": "a.py", "code": "x" * 2000}]},
            "memory": {"content": []},
        }
        optimized, stats = optimizer.optimize_context(layers, scope="code")
        assert isinstance(optimized, dict)
        assert stats.saved_tokens >= 0
        assert 0 < stats.compression_ratio <= 1.0

    def test_optimize_context_aggressive(self, optimizer):
        layers = {
            "global": {"content": "x" * 10000},
            "task": {"content": "x" * 5000},
            "retrieved": {"content": "x" * 15000},
            "memory": {"content": "x" * 5000},
        }
        _, stats_balanced = optimizer.optimize_context(layers, scope="general", strategy="balanced")
        _, stats_aggressive = optimizer.optimize_context(layers, scope="general", strategy="aggressive")
        assert stats_aggressive.total_tokens <= stats_balanced.total_tokens


class TestTokenStats:
    def test_defaults(self):
        stats = TokenStats()
        assert stats.total_tokens == 0
        assert stats.saved_tokens == 0
        assert stats.compression_ratio == 1.0
        assert stats.layer_usage == {}
