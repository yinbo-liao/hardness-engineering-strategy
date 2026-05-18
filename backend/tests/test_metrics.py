import pytest
from backend.app.harness.metrics import MetricsCollector, MetricValue


class TestMetricValue:
    def test_defaults(self):
        mv = MetricValue(name="test_metric", value=1.0, labels={})
        assert mv.name == "test_metric"
        assert mv.type == "gauge"
        assert mv.timestamp > 0


class TestMetricsCollector:
    @pytest.fixture
    def collector(self):
        return MetricsCollector()

    def test_gauge_set_and_get(self, collector):
        collector.gauge("tasks_active", 5)
        all_metrics = collector.get_all()
        names = [m.name for m in all_metrics]
        assert "tasks_active" in names

    def test_counter_increments(self, collector):
        collector.counter("tasks_completed", 1)
        collector.counter("tasks_completed", 1)
        collector.counter("tasks_completed", 2)
        all_metrics = collector.get_all()
        for m in all_metrics:
            if m.name == "tasks_completed":
                assert m.value == 4
                return
        pytest.fail("Counter not found")

    def test_gauge_overwrites(self, collector):
        collector.gauge("temp", 10)
        collector.gauge("temp", 20)
        all_metrics = collector.get_all()
        for m in all_metrics:
            if m.name == "temp":
                assert m.value == 20
                return
        pytest.fail("Gauge not found")

    def test_observe_records_values(self, collector):
        collector.observe("latency_ms", 10)
        collector.observe("latency_ms", 20)
        collector.observe("latency_ms", 30)
        all_metrics = collector.get_all()
        sum_found = False
        count_found = False
        for m in all_metrics:
            if m.name == "latency_ms_sum":
                assert m.value == pytest.approx(60.0)
                sum_found = True
            if m.name == "latency_ms_count":
                assert m.value == 3
                count_found = True
        assert sum_found and count_found

    def test_labels_create_separate_metrics(self, collector):
        collector.gauge("task_status", 1, labels={"status": "running"})
        collector.gauge("task_status", 3, labels={"status": "completed"})
        all_metrics = collector.get_all()
        status_metrics = [m for m in all_metrics if m.name == "task_status"]
        assert len(status_metrics) == 2

    def test_render_prometheus_format(self, collector):
        collector.gauge("test_gauge", 42)
        output = collector.render_prometheus()
        assert "# HELP test_gauge" in output
        assert "# TYPE test_gauge gauge" in output
        assert "test_gauge 42" in output

    def test_get_all_empty_collector(self, collector):
        assert collector.get_all() == []

    def test_counter_starts_at_zero(self, collector):
        collector.counter("new_counter")
        collector.counter("new_counter")
        all_metrics = collector.get_all()
        for m in all_metrics:
            if m.name == "new_counter":
                assert m.value == 2
