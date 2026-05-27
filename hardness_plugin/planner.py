import asyncio
import hashlib
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskNode:
    id: str
    description: str
    action: Optional[Callable] = None
    deps: List[str] = field(default_factory=list)
    task_type: str = "code"
    retry_count: int = 3
    timeout_seconds: int = 300
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[dict] = None
    error_log: List[str] = field(default_factory=list)
    checkpoint_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "deps": self.deps,
            "type": self.task_type,
            "result": self.result,
            "error_log": self.error_log,
            "checkpoint": self.checkpoint_data,
        }


class CycleDetectedError(Exception):
    pass


class TaskPlanner:
    """
    DAG-based task planner with topological sorting via Kahn's algorithm.

    Key properties:
    - Tasks are idempotent (safe to retry after partial completion)
    - Dependencies are explicit (no hidden coupling between tasks)
    - Execution order is deterministic (topological sort)
    - State is checkpointed atomically after each task completes
    """

    def __init__(self, state_store_path: str = "Hardness_state.json"):
        self.tasks: Dict[str, TaskNode] = {}
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)
        self.state_store_path = state_store_path
        self._loaded_state: dict = {}
        self._load_state()

    def add_task(self, node: TaskNode) -> None:
        if node.id in self.tasks:
            raise ValueError(f"Task {node.id} already exists in planner")

        # Restore state from checkpoint if available
        if node.id in self._loaded_state:
            saved = self._loaded_state[node.id]
            node.status = TaskStatus(saved["status"])
            node.result = saved.get("result")
            node.error_log = saved.get("error_log", [])
            node.checkpoint_data = saved.get("checkpoint", {})

        self.tasks[node.id] = node

        for dep in node.deps:
            if dep not in self.tasks:
                raise ValueError(
                    f"Dependency '{dep}' for task '{node.id}' does not exist"
                )
            self.graph[dep].append(node.id)
            self.reverse_graph[node.id].append(dep)

        # Ensure reverse graph entry exists even for tasks with no deps
        if node.id not in self.reverse_graph:
            self.reverse_graph[node.id] = []

    def remove_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        dependents = list(self.graph.get(task_id, []))
        if dependents:
            raise ValueError(
                f"Cannot remove task {task_id}: still depended on by {dependents}"
            )

        for dep in self.tasks[task_id].deps:
            self.graph[dep].remove(task_id)
            if not self.graph[dep]:
                del self.graph[dep]

        del self.reverse_graph[task_id]
        del self.tasks[task_id]

    def get_execution_order(self) -> List[str]:
        in_degree = {
            tid: len(self.reverse_graph.get(tid, []))
            for tid in self.tasks
        }
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)

            for neighbor in self.graph.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.tasks):
            remaining = set(self.tasks.keys()) - set(order)
            raise CycleDetectedError(f"Cycle detected involving tasks: {remaining}")

        return order

    async def execute_with_recovery(self, orchestrator) -> List[str]:
        order = self.get_execution_order()
        completed: List[str] = []

        for task_id in order:
            task = self.tasks[task_id]

            if task.status == TaskStatus.COMPLETED:
                completed.append(task_id)
                continue

            task.status = TaskStatus.RUNNING
            self._save_state()

            success = False
            for attempt in range(1, task.retry_count + 1):
                try:
                    result = await asyncio.wait_for(
                        orchestrator.execute_task(task),
                        timeout=task.timeout_seconds,
                    )
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    self._save_state()
                    completed.append(task_id)
                    success = True
                    break
                except asyncio.TimeoutError:
                    task.error_log.append(
                        f"Attempt {attempt}/{task.retry_count}: timed out after {task.timeout_seconds}s"
                    )
                except Exception as e:
                    task.error_log.append(
                        f"Attempt {attempt}/{task.retry_count}: {e!s}"
                    )

            if not success:
                task.status = TaskStatus.FAILED
                self._save_state()
                await self._trigger_feedback_loop(task, orchestrator)
                raise RuntimeError(
                    f"Task '{task_id}' failed after {task.retry_count} attempts"
                )

        return completed

    def _save_state(self) -> None:
        state = {tid: node.to_dict() for tid, node in self.tasks.items()}
        content = json.dumps(state, indent=2, sort_keys=True)
        tmp_path = f"{self.state_store_path}.tmp"

        with open(tmp_path, "w") as f:
            f.write(content)

        os.replace(tmp_path, self.state_store_path)

    def _load_state(self) -> None:
        try:
            with open(self.state_store_path) as f:
                state = json.load(f)

            self._loaded_state = state

            for tid, data in state.items():
                if tid in self.tasks:
                    self.tasks[tid].status = TaskStatus(data["status"])
                    self.tasks[tid].result = data.get("result")
                    self.tasks[tid].error_log = data.get("error_log", [])
                    self.tasks[tid].checkpoint_data = data.get("checkpoint", {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    async def _trigger_feedback_loop(
        self, failed_task: TaskNode, orchestrator
    ) -> None:
        feedback = {
            "failed_task": failed_task.id,
            "errors": failed_task.error_log,
            "context": failed_task.description,
            "checkpoint": failed_task.checkpoint_data,
        }
        await orchestrator.reflect_and_fix(feedback)

    def compute_state_hash(self) -> str:
        state = {tid: node.to_dict() for tid, node in self.tasks.items()}
        content = json.dumps(state, indent=2, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
