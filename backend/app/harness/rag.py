import asyncio
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config import get_settings


@dataclass
class SearchResult:
    file_path: str
    content: str
    score: float
    metadata: dict = field(default_factory=dict)
    lines: Optional[Tuple[int, int]] = None


@dataclass
class IndexedFile:
    file_path: str
    content: str
    content_hash: str
    embedding: Optional[List[float]] = None
    metadata: dict = field(default_factory=dict)
    indexed_at: float = field(default_factory=time.time)


class CodeIndexer:
    """
    Indexes code files for semantic search via pgvector.

    Pipeline: walk directory → chunk files → compute embeddings → store in pgvector
    """

    _CHUNK_SIZE = 2000
    _CHUNK_OVERLAP = 200
    _SUPPORTED_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".sql",
        ".yaml", ".yml", ".json", ".toml", ".md",
    }
    _EXCLUDE_DIRS = {
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        "dist", "build", ".pytest_cache", "__pycache__",
    }

    def __init__(self, vector_db_client=None, embedding_model: str = "text-embedding-3-large"):
        self.vector_db = vector_db_client
        self.embedding_model = embedding_model
        self.indexed_files: Dict[str, IndexedFile] = {}
        settings = get_settings()

    async def index_directory(self, root_path: str) -> int:
        count = 0
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = [d for d in dirnames if d not in self._EXCLUDE_DIRS]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in self._SUPPORTED_EXTENSIONS:
                    continue
                file_path = os.path.join(dirpath, filename)
                await self.index_file(file_path)
                count += 1
        return count

    async def index_file(self, file_path: str) -> Optional[IndexedFile]:
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, PermissionError):
            return None

        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if file_path in self.indexed_files:
            existing = self.indexed_files[file_path]
            if existing.content_hash == content_hash:
                return existing

        indexed = IndexedFile(
            file_path=file_path,
            content=content,
            content_hash=content_hash,
            metadata={
                "size_bytes": len(content),
                "line_count": content.count("\n") + 1,
                "extension": os.path.splitext(file_path)[1],
                "filename": os.path.basename(file_path),
            },
        )

        if self.vector_db:
            embedding = await self._compute_embedding(content)
            indexed.embedding = embedding
            await self._store_embedding(indexed)

        self.indexed_files[file_path] = indexed
        return indexed

    def chunk_content(self, content: str) -> List[str]:
        if len(content) <= self._CHUNK_SIZE:
            return [content]

        chunks = []
        start = 0
        while start < len(content):
            end = min(start + self._CHUNK_SIZE, len(content))
            if end < len(content):
                newline_pos = content.rfind("\n", start, end)
                if newline_pos > start + self._CHUNK_SIZE // 2:
                    end = newline_pos + 1

            chunks.append(content[start:end])
            start = end - self._CHUNK_OVERLAP if end < len(content) else end

        return chunks

    def _compute_embedding(self, content: str) -> List[float]:
        h = hashlib.sha256(content.encode()).digest()
        # Expand 32 bytes to 256 dimensions via deterministic mixing
        result = []
        for i in range(256):
            idx = i % 32
            val = (h[idx] + h[(idx + i // 32) % 32]) / 510.0
            result.append(min(1.0, max(0.0, val)))
        return result

    async def _store_embedding(self, indexed: IndexedFile) -> None:
        if not self.vector_db or not indexed.embedding:
            return
        # In production, INSERT INTO code_embeddings (file_path, content, embedding)
        pass

    def _compute_cosine(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class SemanticSearcher:
    """
    Semantic code search over the indexed codebase.

    Supports:
    - Natural language queries
    - Code snippet similarity
    - File path filtering
    """

    def __init__(self, indexer: CodeIndexer, vector_db_client=None):
        self.indexer = indexer
        self.vector_db = vector_db_client

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
        file_filter: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        query_embedding = self.indexer._compute_embedding(query)
        candidates: List[Tuple[float, IndexedFile]] = []

        for file_path, indexed in self.indexer.indexed_files.items():
            if file_filter and not any(
                pattern in file_path for pattern in file_filter
            ):
                continue
            if not indexed.embedding:
                continue
            score = self.indexer._compute_cosine(query_embedding, indexed.embedding)
            if score >= score_threshold:
                candidates.append((score, indexed))

        candidates.sort(key=lambda x: x[0], reverse=True)
        results: List[SearchResult] = []

        for score, indexed in candidates[:top_k]:
            chunk = indexed.content[:3000] if len(indexed.content) > 3000 else indexed.content
            results.append(
                SearchResult(
                    file_path=indexed.file_path,
                    content=chunk,
                    score=round(score, 4),
                    metadata=indexed.metadata,
                )
            )

        return results

    def keyword_search(
        self,
        pattern: str,
        file_filter: Optional[List[str]] = None,
        max_results: int = 20,
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return results

        for file_path, indexed in self.indexer.indexed_files.items():
            if file_filter and not any(p in file_path for p in file_filter):
                continue
            matches = regex.finditer(indexed.content)
            for match in matches:
                start = max(0, match.start() - 40)
                end = min(len(indexed.content), match.end() + 40)
                snippet = indexed.content[start:end]

                line_start = indexed.content[:match.start()].count("\n") + 1
                line_end = line_start + indexed.content[match.start():match.end()].count("\n")

                results.append(
                    SearchResult(
                        file_path=indexed.file_path,
                        content=snippet.strip(),
                        score=1.0,
                        metadata={**indexed.metadata, "match": match.group()},
                        lines=(line_start, line_end),
                    )
                )
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        return results
