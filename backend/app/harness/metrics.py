"""
Prometheus metrics for the Harness Control Plane.

Tracks:
- Task lifecycle (created, running, completed, failed)
- Approval queue depth
- Agent loop iterations
- Evaluation dimension scores
- Sandbox container count
- API request latency and rate
"""

import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class MetricValue:
    name: str
    value: float
    labels: Dict[str, str]
    type: str = "gauge"  # gauge, counter, histogram
    help: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class MetricsCollector:
    """
    In-process metrics collector.

    In production, these would be registered with prometheus-client
    and exposed via the /metrics endpoint.
    """

    def __init__(self):
        self._gauges: Dict[str, float] = {}
        self._counters: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}

    def gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        key = self._key(name, labels)
        self._gauges[key] = value

    def counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        key = self._key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def observe(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        key = self._key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def get_all(self) -> list:
        results: list = []

        for key, value in self._gauges.items():
            name, labels = self._parse_key(key)
            results.append(
                MetricValue(name=name, value=value, labels=labels, type="gauge")
            )

        for key, value in self._counters.items():
            name, labels = self._parse_key(key)
            results.append(
                MetricValue(name=name, value=value, labels=labels, type="counter")
            )

        for key, values in self._histograms.items():
            name, labels = self._parse_key(key)
            if values:
                results.append(
                    MetricValue(
                        name=f"{name}_sum",
                        value=sum(values),
                        labels=labels,
                        type="histogram",
                    )
                )
                results.append(
                    MetricValue(
                        name=f"{name}_count",
                        value=len(values),
                        labels=labels,
                        type="histogram",
                    )
                )

        return results

    def render_prometheus(self) -> str:
        lines: list = []
        for m in self.get_all():
            label_str = ",".join(f'{k}="{v}"' for k, v in m.labels.items())
            label_part = f"{{{label_str}}}" if label_str else ""
            lines.append(f"# HELP {m.name} {m.help}")
            lines.append(f"# TYPE {m.name} {m.type}")
            lines.append(f"{m.name}{label_part} {m.value}")
        return "\n".join(lines) + "\n"

    def _key(self, name: str, labels: Dict[str, str] = None) -> str:
        if labels:
            sorted_labels = sorted(labels.items())
            return name + ":" + ",".join(f"{k}={v}" for k, v in sorted_labels)
        return name

    def _parse_key(self, key: str) -> tuple:
        if ":" in key:
            name, label_part = key.split(":", 1)
            labels = {}
            for pair in label_part.split(","):
                k, v = pair.split("=", 1)
                labels[k] = v
            return name, labels
        return key, {}
