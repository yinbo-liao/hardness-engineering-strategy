import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TaskMemoryEntry:
    task_id: str
    description: str
    task_type: str
    solution_summary: str
    success_rate: float
    iterations_used: int
    cost: float
    execution_time_ms: int
    tags: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    created_at: float = field(default_factory=time.time)
    accessed_count: int = 0
    last_accessed: float = 0.0


class TaskMemoryStore:
    """
    Stores completed task solutions for future retrieval.

    Key features:
    - Similarity-based retrieval for past task solutions
    - Success rate tracking for quality filtering
    - Tag-based categorization
    - LRU eviction for memory management
    """

    def __init__(
        self,
        max_entries: int = 1000,
        similarity_threshold: float = 0.8,
        vector_db_client=None,
    ):
        self.max_entries = max_entries
        self.similarity_threshold = similarity_threshold
        self.vector_db = vector_db_client
        self.entries: Dict[str, TaskMemoryEntry] = {}
        self.tag_index: Dict[str, set] = {}

    async def store(self, entry: TaskMemoryEntry) -> None:
        if len(self.entries) >= self.max_entries:
            self._evict_lru()

        self.entries[entry.task_id] = entry

        for tag in entry.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(entry.task_id)

        if self.vector_db and not entry.embedding:
            entry.embedding = self._compute_embedding(entry.description)

    def retrieve(self, task_id: str) -> Optional[TaskMemoryEntry]:
        entry = self.entries.get(task_id)
        if entry:
            entry.accessed_count += 1
            entry.last_accessed = time.time()
        return entry

    async def find_similar(
        self,
        query: str,
        top_k: int = 5,
        min_success_rate: float = 0.8,
    ) -> List[TaskMemoryEntry]:
        query_embedding = self._compute_embedding(query)
        scored: List[tuple] = []

        for entry in self.entries.values():
            if entry.success_rate < min_success_rate:
                continue
            if not entry.embedding:
                entry.embedding = self._compute_embedding(entry.description)
            score = self._cosine_similarity(query_embedding, entry.embedding)
            if score >= self.similarity_threshold:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:top_k]]

        for entry in results:
            entry.accessed_count += 1
            entry.last_accessed = time.time()

        return results

    async def find_by_tags(
        self,
        tags: List[str],
        require_all: bool = False,
        limit: int = 10,
    ) -> List[TaskMemoryEntry]:
        if not tags:
            return []

        if require_all:
            task_ids = self.tag_index.get(tags[0], set()).copy()
            for tag in tags[1:]:
                task_ids &= self.tag_index.get(tag, set())
        else:
            task_ids: set = set()
            for tag in tags:
                task_ids |= self.tag_index.get(tag, set())

        entries = [self.entries[tid] for tid in task_ids if tid in self.entries]
        entries.sort(key=lambda e: e.success_rate, reverse=True)
        return entries[:limit]

    async def get_statistics(self) -> dict:
        if not self.entries:
            return {
                "total_entries": 0,
                "avg_success_rate": 0,
                "avg_cost": 0,
                "avg_iterations": 0,
                "total_cost": 0,
            }

        entries = list(self.entries.values())
        return {
            "total_entries": len(entries),
            "avg_success_rate": sum(e.success_rate for e in entries) / len(entries),
            "avg_cost": sum(e.cost for e in entries) / len(entries),
            "avg_iterations": sum(e.iterations_used for e in entries) / len(entries),
            "total_cost": sum(e.cost for e in entries),
            "most_common_tags": sorted(
                self.tag_index.keys(),
                key=lambda t: len(self.tag_index[t]),
                reverse=True,
            )[:10],
        }

    def _evict_lru(self) -> None:
        if not self.entries:
            return
        oldest = min(
            self.entries.keys(),
            key=lambda tid: self.entries[tid].last_accessed or self.entries[tid].created_at,
        )
        entry = self.entries.pop(oldest)
        for tag in entry.tags:
            if tag in self.tag_index:
                self.tag_index[tag].discard(oldest)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]

    def _compute_embedding(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode()).digest()
        result = []
        for i in range(256):
            idx = i % 32
            val = (h[idx] + h[(idx + i // 32) % 32]) / 510.0
            result.append(min(1.0, max(0.0, val)))
        return result

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
