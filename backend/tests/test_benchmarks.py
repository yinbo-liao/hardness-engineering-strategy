import time

import pytest
from backend.app.harness.benchmarks import BenchmarkRunner, BenchmarkResult, CostBreakdown


class TestBenchmarkResult:
    def test_defaults(self):
        result = BenchmarkResult(
            name="test_bench",
            iterations=10,
            total_time_ms=100,
            avg_time_ms=10,
            min_time_ms=5,
            max_time_ms=20,
            p50_time_ms=9,
            p95_time_ms=18,
            p99_time_ms=19,
            std_dev_ms=3.5,
        )
        assert result.name == "test_bench"
        assert result.iterations == 10


class TestBenchmarkRunner:
    @pytest.fixture
    def runner(self):
        return BenchmarkRunner()

    @pytest.mark.asyncio
    async def test_benchmark_sync_function(self, runner):
        def sync_op():
            time.sleep(0.01)
        result = await runner.benchmark("sync_test", sync_op, iterations=5, warmup=1)
        assert result.iterations == 5
        # All timings should be positive (at least 1ms each for 0.01s sleep)
        assert len([t for t in result.timings if t > 0]) >= 3
        assert result.min_time_ms <= result.max_time_ms
        assert result.p50_time_ms >= result.min_time_ms

    @pytest.mark.asyncio
    async def test_benchmark_async_function(self, runner):
        async def async_op():
            import asyncio
            await asyncio.sleep(0.001)
        result = await runner.benchmark("async_test", async_op, iterations=5, warmup=1)
        assert result.iterations == 5
        assert result.avg_time_ms > 0

    def test_track_cost(self, runner):
        breakdown = runner.track_cost(
            task_id="task-1",
            prompt_tokens=5000,
            completion_tokens=2000,
            model="claude-sonnet-4-6",
        )
        assert breakdown.task_id == "task-1"
        assert breakdown.total_cost > 0
        assert breakdown.token_usage["total_tokens"] == 7000

    def test_cost_estimation(self, runner):
        runner.track_cost("task-1", prompt_tokens=5000, completion_tokens=2000)
        savings = runner.estimate_savings("task-1", baseline_tokens=10000)
        assert savings >= 0

    def test_get_summary(self, runner):
        runner.track_cost("a", prompt_tokens=1000, completion_tokens=500)
        runner.track_cost("b", prompt_tokens=2000, completion_tokens=800)
        summary = runner.get_summary()
        assert summary["tasks_tracked"] == 2
        assert summary["total_cost"] > 0
        assert summary["avg_cost_per_task"] > 0
        assert summary["total_tokens"] == 4300
        assert summary["avg_tokens_per_task"] == 2150

    def test_percentile(self, runner):
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        p50 = runner._percentile(data, 50)
        p95 = runner._percentile(data, 95)
        p99 = runner._percentile(data, 99)
        assert p50 == pytest.approx(5.5, abs=0.01)
        assert p95 > p50
        assert p99 >= p95

    def test_empty_percentile(self, runner):
        assert runner._percentile([], 50) == 0.0

    @pytest.mark.asyncio
    async def test_benchmark_handles_exceptions(self, runner):
        def failing_func():
            raise RuntimeError("expected test error")
        result = await runner.benchmark("failing", failing_func, iterations=3, warmup=0)
        assert result.iterations == 3
        assert result.timings is not None

    @pytest.mark.asyncio
    async def test_benchmark_stores_result(self, runner):
        await runner.benchmark("stored", lambda: None, iterations=3, warmup=0)
        assert "stored" in runner._results
