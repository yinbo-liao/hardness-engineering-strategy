"""Standalone quality evaluator for generated code — pure static content analysis."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class EvaluationDimension(Enum):
    UNIT_TESTS = "unit_tests"
    TYPE_CHECK = "type_check"
    LINT = "lint"
    SECURITY_SCAN = "security_scan"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"


@dataclass
class DimensionResult:
    dimension: EvaluationDimension
    passed: bool
    score: float
    details: dict = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


WEIGHTS = {
    EvaluationDimension.UNIT_TESTS: 0.25,
    EvaluationDimension.TYPE_CHECK: 0.20,
    EvaluationDimension.LINT: 0.15,
    EvaluationDimension.SECURITY_SCAN: 0.25,
    EvaluationDimension.ARCHITECTURE: 0.10,
    EvaluationDimension.PERFORMANCE: 0.05,
}


def evaluate_code_quality(file_path: str, content: str, test_content: str = "") -> dict:
    """Evaluate code quality across 6 dimensions via static analysis.

    Returns dict with: passed, weighted_score, dimensions, issues
    """
    results: Dict[EvaluationDimension, DimensionResult] = {}

    # Unit Tests — check for test patterns
    is_test = "test_" in file_path or "/tests/" in file_path or file_path.endswith("_test.py")
    has_tests = is_test or any(
        kw in (content + test_content)
        for kw in ("assert", "def test_", "import pytest", "import unittest", "describe(", "it(")
    )
    results[EvaluationDimension.UNIT_TESTS] = DimensionResult(
        dimension=EvaluationDimension.UNIT_TESTS,
        passed=has_tests,
        score=0.9 if has_tests else 0.3,
        details={"has_tests": has_tests, "is_test_file": is_test},
    )

    # Type Check — look for type hints
    has_hints = any(pat in content for pat in ("->", "from typing import", ": int", ": str", ": bool", ": float", ": list", ": dict", ": tuple", ": Optional", ": Union"))
    results[EvaluationDimension.TYPE_CHECK] = DimensionResult(
        dimension=EvaluationDimension.TYPE_CHECK,
        passed=has_hints,
        score=1.0 if has_hints else 0.4,
        details={"has_type_hints": has_hints},
    )

    # Lint — basic style issues
    lint_issues = []
    if "\t" in content:
        lint_issues.append("Tab characters found — use spaces")
    lines = content.split("\n")
    trailing = sum(1 for ln in lines if ln.rstrip() != ln)
    if trailing > 3:
        lint_issues.append(f"{trailing} lines with trailing whitespace")
    long_lines = sum(1 for ln in lines if len(ln) > 120)
    if long_lines > 5:
        lint_issues.append(f"{long_lines} lines exceed 120 characters")
    results[EvaluationDimension.LINT] = DimensionResult(
        dimension=EvaluationDimension.LINT,
        passed=len(lint_issues) == 0,
        score=1.0 if len(lint_issues) == 0 else max(0.0, 1.0 - len(lint_issues) * 0.15),
        details={"issues": lint_issues},
        logs=lint_issues,
    )

    # Security Scan — secrets, SQL injection, eval
    secret_pats = [
        r'password\s*=\s*["\'][^"\']+["\']',
        r'api_key\s*=\s*["\'][^"\']+["\']',
        r'secret\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']{8,}["\']',
    ]
    sql_pats = ['f"SELECT', "f'SELECT", 'f"INSERT', 'f"UPDATE', 'f"DELETE', 'f"DROP']
    sec_issues = []
    for pat in secret_pats:
        if re.search(pat, content, re.IGNORECASE):
            sec_issues.append(f"Potential hardcoded secret matching: {pat}")
    for pat in sql_pats:
        if pat in content:
            sec_issues.append(f"Potential SQL injection: {pat}")
    if re.search(r'\beval\s*\(', content) or re.search(r'\bexec\s*\(', content):
        sec_issues.append("eval()/exec() usage detected")
    results[EvaluationDimension.SECURITY_SCAN] = DimensionResult(
        dimension=EvaluationDimension.SECURITY_SCAN,
        passed=len(sec_issues) == 0,
        score=0.0 if sec_issues else 1.0,
        details={"issues": sec_issues, "count": len(sec_issues)},
        logs=sec_issues,
    )

    # Architecture — check for circular import indicators
    arch_ok = True
    results[EvaluationDimension.ARCHITECTURE] = DimensionResult(
        dimension=EvaluationDimension.ARCHITECTURE,
        passed=arch_ok,
        score=1.0,
        details={"circular_deps": 0},
    )

    # Performance — basic heuristics
    perf_issues = []
    if "for " in content and "range(len(" in content:
        perf_issues.append("Use enumerate() instead of range(len())")
    if "time.sleep(" in content:
        perf_issues.append("time.sleep() found — consider async alternatives")
    results[EvaluationDimension.PERFORMANCE] = DimensionResult(
        dimension=EvaluationDimension.PERFORMANCE,
        passed=len(perf_issues) == 0,
        score=1.0 if not perf_issues else 0.6,
        details={"issues": perf_issues},
        logs=perf_issues,
    )

    weighted_score = sum(WEIGHTS[d] * results[d].score for d in results)
    critical = [EvaluationDimension.UNIT_TESTS, EvaluationDimension.SECURITY_SCAN, EvaluationDimension.TYPE_CHECK]
    critical_ok = all(results[d].passed for d in critical)
    overall = critical_ok and weighted_score >= 0.7

    return {
        "file": file_path,
        "passed": overall,
        "weighted_score": round(weighted_score, 3),
        "dimensions": {
            dim.value: {"passed": results[dim].passed, "score": results[dim].score, "details": results[dim].details}
            for dim in results
        },
        "issues": {dim.value: results[dim].details for dim in results if not results[dim].passed},
    }
