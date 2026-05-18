import pytest
from backend.app.harness.planner import (
    TaskPlanner,
    TaskNode,
    TaskStatus,
    CycleDetectedError,
)


class TestTaskNode:
    def test_defaults(self):
        node = TaskNode(id="t1", description="test task")
        assert node.id == "t1"
        assert node.status == TaskStatus.PENDING
        assert node.deps == []
        assert node.retry_count == 3
        assert node.task_type == "code"

    def test_to_dict(self):
        node = TaskNode(id="t2", description="build API", deps=["t1"])
        d = node.to_dict()
        assert d["id"] == "t2"
        assert d["status"] == "pending"
        assert d["deps"] == ["t1"]


class TestTaskPlannerBasic:
    def test_add_task(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        node = TaskNode(id="a", description="first")
        planner.add_task(node)
        assert "a" in planner.tasks
        assert planner.tasks["a"].status == TaskStatus.PENDING

    def test_duplicate_task_raises(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="x", description="task"))
        with pytest.raises(ValueError, match="already exists"):
            planner.add_task(TaskNode(id="x", description="dup"))

    def test_missing_dependency_raises(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        with pytest.raises(ValueError, match="does not exist"):
            planner.add_task(TaskNode(id="b", description="has bad dep", deps=["nonexistent"]))

    def test_remove_task_with_dependents_raises(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="root", description="root"))
        planner.add_task(TaskNode(id="child", description="child", deps=["root"]))
        with pytest.raises(ValueError, match="still depended on"):
            planner.remove_task("root")

    def test_remove_orphan_task(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="orphan", description="no deps or dependents"))
        planner.remove_task("orphan")
        assert "orphan" not in planner.tasks


class TestTopologicalSort:
    def test_linear_chain(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="1", description="setup"))
        planner.add_task(TaskNode(id="2", description="build", deps=["1"]))
        planner.add_task(TaskNode(id="3", description="test", deps=["2"]))
        order = planner.get_execution_order()
        assert order == ["1", "2", "3"]

    def test_diamond_dag(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="a", description="root"))
        planner.add_task(TaskNode(id="b1", description="branch 1", deps=["a"]))
        planner.add_task(TaskNode(id="b2", description="branch 2", deps=["a"]))
        planner.add_task(TaskNode(id="c", description="merge", deps=["b1", "b2"]))
        order = planner.get_execution_order()
        assert order[0] == "a"
        assert order[3] == "c"
        assert set(order[1:3]) == {"b1", "b2"}

    def test_independent_tasks(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="x", description="x"))
        planner.add_task(TaskNode(id="y", description="y"))
        planner.add_task(TaskNode(id="z", description="z"))
        order = planner.get_execution_order()
        assert set(order) == {"x", "y", "z"}

    def test_cycle_detection(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="p", description="p"))
        planner.add_task(TaskNode(id="q", description="q", deps=["p"]))
        # Manually inject a cycle
        planner.tasks["p"].deps.append("q")
        planner.reverse_graph["p"].append("q")
        planner.graph["q"].append("p")
        with pytest.raises(CycleDetectedError, match="Cycle detected"):
            planner.get_execution_order()


class TestStateCheckpointing:
    def test_save_and_load_state(self, temp_state_file):
        p1 = TaskPlanner(temp_state_file)
        p1.add_task(TaskNode(id="s1", description="stateful"))
        p1.tasks["s1"].status = TaskStatus.COMPLETED
        p1.tasks["s1"].result = {"files": ["a.py"]}
        p1._save_state()

        p2 = TaskPlanner(temp_state_file)
        p2.add_task(TaskNode(id="s1", description="stateful"))
        assert p2.tasks["s1"].status == TaskStatus.COMPLETED
        assert p2.tasks["s1"].result == {"files": ["a.py"]}

    def test_compute_state_hash(self, temp_state_file):
        planner = TaskPlanner(temp_state_file)
        planner.add_task(TaskNode(id="h1", description="hash test"))
        h1 = planner.compute_state_hash()
        planner.add_task(TaskNode(id="h2", description="hash test 2"))
        h2 = planner.compute_state_hash()
        assert h1 != h2
