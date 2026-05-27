"""Hardness Engineering Plugin for Claude Code.

Provides governance, evaluation, planning, and quality enforcement
as a lightweight Python package integrated with Claude Code hooks.
"""

from hardness_plugin.governance import AuditEntry, ConstraintRule, Governance, RiskLevel
from hardness_plugin.planner import TaskNode, TaskPlanner, TaskStatus
from hardness_plugin.token_optimizer import TokenOptimizer
from hardness_plugin.task_memory import TaskMemoryEntry, TaskMemoryStore
from hardness_plugin.project_config import find_project_root, load_project_config
from hardness_plugin.evaluator import evaluate_code_quality
from hardness_plugin.benchmarks import BenchmarkResult, BenchmarkRunner
from hardness_plugin.metrics import MetricValue, MetricsCollector

__version__ = "1.0.0"
__all__ = [
    "Governance",
    "ConstraintRule",
    "AuditEntry",
    "RiskLevel",
    "TaskPlanner",
    "TaskNode",
    "TaskStatus",
    "TokenOptimizer",
    "TaskMemoryStore",
    "TaskMemoryEntry",
    "load_project_config",
    "find_project_root",
    "evaluate_code_quality",
    "BenchmarkRunner",
    "BenchmarkResult",
    "MetricsCollector",
    "MetricValue",
]
