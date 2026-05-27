import asyncio
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p50_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    std_dev_ms: float
    timings: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total": self.total_time_ms,
            "mean": self.avg_time_ms,
            "min": self.min_time_ms,
            "max": self.max_time_ms,
            "p50": self.p50_time_ms,
            "p95": self.p95_time_ms,
            "p99": self.p99_time_ms,
            "std": self.std_dev_ms,
        }


@dataclass
class CostBreakdown:
    task_id: str
    total_cost: float
    token_usage: dict = field(default_factory=dict)
    phase_costs: Dict[str, float] = field(default_factory=dict)
    estimated_savings: float = 0.0


class BenchmarkRunner:
    """
    Performance benchmarking for Hardness operations.

    Measures:
    - Execution time percentiles (min, p50, p95, p99, max)
    - Cost per task and per phase
    - Token usage tracking
    """

    def __init__(self):
        self._results: Dict[str, BenchmarkResult] = {}
        self._costs: Dict[str, CostBreakdown] = {}

    async def benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 10,
        warmup: int = 2,
        *args,
        **kwargs,
    ) -> BenchmarkResult:
        for _ in range(warmup):
            try:
                await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception:
                pass

        timings: List[float] = []
        for _ in range(iterations):
            start = time.monotonic()
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            except Exception:
                pass
            elapsed = (time.monotonic() - start) * 1000
            timings.append(elapsed)

        if not timings:
            return BenchmarkResult(
                name=name, iterations=iterations, total_time_ms=0,
                avg_time_ms=0, min_time_ms=0, max_time_ms=0,
                p50_time_ms=0, p95_time_ms=0, p99_time_ms=0, std_dev_ms=0,
            )

        sorted_t = sorted(timings)
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time_ms=sum(timings),
            avg_time_ms=statistics.mean(timings),
            min_time_ms=min(timings),
            max_time_ms=max(timings),
            p50_time_ms=self._percentile(sorted_t, 50),
            p95_time_ms=self._percentile(sorted_t, 95),
            p99_time_ms=self._percentile(sorted_t, 99),
            std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
            timings=timings,
        )
        self._results[name] = result
        return result

    def track_cost(
        self,
        task_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        phase_costs: Optional[Dict[str, float]] = None,
        model: str = "claude-sonnet-4-6",
    ) -> CostBreakdown:
        pricing = {
            "claude-sonnet-4-6": (3.0, 15.0),
            "claude-opus-4-7": (15.0, 75.0),
            "claude-haiku-4-5": (0.80, 4.0),
        }
        price_per_1k_prompt, price_per_1k_completion = pricing.get(
            model, (3.0, 15.0)
        )

        prompt_cost = (prompt_tokens / 1000) * price_per_1k_prompt
        completion_cost = (completion_tokens / 1000) * price_per_1k_completion
        total = prompt_cost + completion_cost

        breakdown = CostBreakdown(
            task_id=task_id,
            total_cost=round(total, 6),
            token_usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            phase_costs=phase_costs or {},
        )
        self._costs[task_id] = breakdown
        return breakdown

    def estimate_savings(self, task_id: str, baseline_tokens: int) -> float:
        current = self._costs.get(task_id)
        if not current:
            return 0.0
        reduction = max(0, baseline_tokens - current.token_usage.get("total_tokens", 0))
        return (reduction / 1000) * 3.0

    def get_summary(self) -> dict:
        total_cost = sum(c.total_cost for c in self._costs.values())
        total_tasks = len(self._costs)
        total_tokens = sum(
            c.token_usage.get("total_tokens", 0) for c in self._costs.values()
        )

        return {
            "benchmarks_run": len(self._results),
            "tasks_tracked": total_tasks,
            "total_cost": round(total_cost, 4),
            "avg_cost_per_task": round(total_cost / total_tasks, 4) if total_tasks > 0 else 0,
            "total_tokens": total_tokens,
            "avg_tokens_per_task": total_tokens // total_tasks if total_tasks > 0 else 0,
            "slowest_operation": max(
                self._results.items(),
                key=lambda x: x[1].avg_time_ms,
            )[0] if self._results else None,
        }

    def _percentile(self, sorted_data: List[float], p: float) -> float:
        if not sorted_data:
            return 0.0
        idx = (p / 100.0) * (len(sorted_data) - 1)
        lo = int(idx)
        hi = min(lo + 1, len(sorted_data) - 1)
        frac = idx - lo
        return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac
