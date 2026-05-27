import pytest
from hardness_plugin.task_memory import TaskMemoryStore, TaskMemoryEntry


class TestTaskMemoryEntry:
    def test_defaults(self):
        entry = TaskMemoryEntry(
            task_id="t1",
            description="test",
            task_type="code",
            solution_summary="done",
            success_rate=0.95,
            iterations_used=2,
            cost=0.05,
            execution_time_ms=1200,
        )
        assert entry.success_rate == 0.95
        assert entry.accessed_count == 0
        assert entry.tags == []


class TestTaskMemoryStore:
    @pytest.fixture
    def store(self):
        return TaskMemoryStore(max_entries=100)

    def test_store_and_retrieve(self, store):
        entry = TaskMemoryEntry(
            task_id="t1", description="first task", task_type="code",
            solution_summary="solved", success_rate=1.0, iterations_used=1,
            cost=0.01, execution_time_ms=500,
        )
        store.entries["t1"] = entry
        result = store.retrieve("t1")
        assert result is not None
        assert result.task_id == "t1"

    def test_retrieve_unknown(self, store):
        assert store.retrieve("nonexistent") is None

    def test_retrieve_increments_access_count(self, store):
        entry = TaskMemoryEntry(
            task_id="t2", description="test", task_type="code",
            solution_summary="ok", success_rate=1.0, iterations_used=1,
            cost=0.0, execution_time_ms=100,
        )
        store.entries["t2"] = entry
        store.retrieve("t2")
        store.retrieve("t2")
        assert entry.accessed_count == 2

    @pytest.mark.asyncio
    async def test_find_similar(self, store):
        e1 = TaskMemoryEntry(
            task_id="a", description="create fastapi endpoint for users",
            task_type="api", solution_summary="created", success_rate=0.95,
            iterations_used=2, cost=0.05, execution_time_ms=1000,
        )
        e2 = TaskMemoryEntry(
            task_id="b", description="build react dashboard component",
            task_type="ui", solution_summary="built", success_rate=0.9,
            iterations_used=3, cost=0.08, execution_time_ms=2000,
        )
        e3 = TaskMemoryEntry(
            task_id="c", description="add database migration for orders",
            task_type="db", solution_summary="migrated", success_rate=0.7,
            iterations_used=5, cost=0.15, execution_time_ms=3000,
        )
        store.entries = {"a": e1, "b": e2, "c": e3}

        results = await store.find_similar(
            "create api endpoint", top_k=3, min_success_rate=0.5,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_find_similar_filters_low_success(self, store):
        e1 = TaskMemoryEntry(
            task_id="x", description="task x", task_type="code",
            solution_summary="failed", success_rate=0.3,
            iterations_used=5, cost=0.5, execution_time_ms=5000,
        )
        store.entries = {"x": e1}

        results = await store.find_similar(
            "task x", top_k=3, min_success_rate=0.8,
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_by_tags(self, store):
        e1 = TaskMemoryEntry(
            task_id="t1", description="task 1", task_type="api",
            solution_summary="done", success_rate=1.0, iterations_used=1,
            cost=0.01, execution_time_ms=500, tags=["api", "fastapi"],
        )
        e2 = TaskMemoryEntry(
            task_id="t2", description="task 2", task_type="ui",
            solution_summary="done", success_rate=1.0, iterations_used=1,
            cost=0.01, execution_time_ms=500, tags=["ui", "react"],
        )
        store.entries = {"t1": e1, "t2": e2}
        store.tag_index = {"api": {"t1"}, "fastapi": {"t1"}, "ui": {"t2"}, "react": {"t2"}}

        results = await store.find_by_tags(["api"], require_all=False)
        assert len(results) == 1
        assert results[0].task_id == "t1"

    @pytest.mark.asyncio
    async def test_find_by_tags_require_all(self, store):
        e1 = TaskMemoryEntry(
            task_id="t1", description="task 1", task_type="api",
            solution_summary="done", success_rate=1.0, iterations_used=1,
            cost=0.01, execution_time_ms=500, tags=["api", "fastapi"],
        )
        store.entries = {"t1": e1}
        store.tag_index = {"api": {"t1"}, "fastapi": {"t1"}}

        results = await store.find_by_tags(["api", "fastapi"], require_all=True)
        assert len(results) == 1

        results2 = await store.find_by_tags(["api", "nonexistent"], require_all=True)
        assert len(results2) == 0

    @pytest.mark.asyncio
    async def test_statistics(self, store):
        e1 = TaskMemoryEntry(
            task_id="a", description="a", task_type="code",
            solution_summary="ok", success_rate=0.9, iterations_used=2,
            cost=0.03, execution_time_ms=800,
        )
        e2 = TaskMemoryEntry(
            task_id="b", description="b", task_type="test",
            solution_summary="ok", success_rate=1.0, iterations_used=1,
            cost=0.01, execution_time_ms=200,
        )
        store.entries = {"a": e1, "b": e2}
        stats = await store.get_statistics()
        assert stats["total_entries"] == 2
        assert stats["avg_success_rate"] == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_eviction_when_full(self, store):
        store.max_entries = 3
        for i in range(5):
            await store.store(TaskMemoryEntry(
                task_id=f"t{i}", description=f"task {i}", task_type="code",
                solution_summary="ok", success_rate=1.0, iterations_used=1,
                cost=0.01, execution_time_ms=100,
            ))
        # After storing 5 with max_entries=3, should have evicted 2, leaving 3
        assert len(store.entries) == 3
