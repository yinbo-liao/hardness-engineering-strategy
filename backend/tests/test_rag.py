import os
import tempfile

import pytest
from backend.app.harness.rag import CodeIndexer, SemanticSearcher, SearchResult


class TestCodeIndexer:
    @pytest.fixture
    def indexer(self):
        return CodeIndexer()

    def test_chunk_small_content(self, indexer):
        chunks = indexer.chunk_content("def foo(): pass")
        assert len(chunks) == 1
        assert chunks[0] == "def foo(): pass"

    def test_chunk_large_content(self, indexer):
        content = "x\n" * 3000
        chunks = indexer.chunk_content(content)
        assert len(chunks) > 1
        assert all(len(c) <= indexer._CHUNK_SIZE + indexer._CHUNK_OVERLAP for c in chunks)

    def test_supported_extensions(self, indexer):
        assert ".py" in indexer._SUPPORTED_EXTENSIONS
        assert ".ts" in indexer._SUPPORTED_EXTENSIONS
        assert ".tsx" in indexer._SUPPORTED_EXTENSIONS
        assert ".bin" not in indexer._SUPPORTED_EXTENSIONS

    def test_exclude_dirs(self, indexer):
        assert "__pycache__" in indexer._EXCLUDE_DIRS
        assert "node_modules" in indexer._EXCLUDE_DIRS

    def test_compute_embedding_dimensions(self, indexer):
        emb = indexer._compute_embedding("test content")
        assert len(emb) == 256
        assert all(0 <= v <= 1.0 for v in emb)

    def test_embedding_deterministic(self, indexer):
        emb1 = indexer._compute_embedding("hello world")
        emb2 = indexer._compute_embedding("hello world")
        assert emb1 == emb2

    def test_embedding_different_for_different_content(self, indexer):
        emb1 = indexer._compute_embedding("hello")
        emb2 = indexer._compute_embedding("world")
        assert emb1 != emb2

    def test_cosine_similarity_identical(self, indexer):
        emb = indexer._compute_embedding("test")
        sim = indexer._compute_cosine(emb, emb)
        assert sim == pytest.approx(1.0, abs=0.001)

    def test_cosine_similarity_zero_for_zeros(self, indexer):
        zero = [0.0] * 256
        sim = indexer._compute_cosine(zero, zero)
        assert sim == 0.0


class TestSemanticSearcher:
    @pytest.fixture
    def indexer(self):
        from backend.app.harness.rag import IndexedFile
        idx = CodeIndexer()
        idx.indexed_files["a.py"] = IndexedFile(
            file_path="a.py",
            content="async def get_users(): pass",
            content_hash="abc",
            embedding=idx._compute_embedding("async def get_users(): pass"),
        )
        idx.indexed_files["b.py"] = IndexedFile(
            file_path="b.py",
            content="class UserDB:\n    def query(self): pass",
            content_hash="def",
            embedding=idx._compute_embedding("class UserDB: query"),
        )
        return idx

    @pytest.fixture
    async def populated_indexer(self):
        idx = CodeIndexer()
        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = os.path.join(tmpdir, "test_code.py")
            with open(py_file, "w") as f:
                f.write("async def fetch_data(url: str) -> dict:\n    return {}")
            await idx.index_file(py_file)
        return idx

    @pytest.mark.asyncio
    async def test_search_returns_results(self, indexer):
        searcher = SemanticSearcher(indexer)
        results = await searcher.search("get users", top_k=2, score_threshold=0.0)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_respects_top_k(self, indexer):
        searcher = SemanticSearcher(indexer)
        results = await searcher.search("query", top_k=1, score_threshold=0.0)
        assert len(results) <= 1

    @pytest.mark.asyncio
    async def test_keyword_search(self, indexer):
        searcher = SemanticSearcher(indexer)
        results = searcher.keyword_search("class", max_results=5)
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_keyword_search_no_match(self, indexer):
        searcher = SemanticSearcher(indexer)
        results = searcher.keyword_search("xyz_not_found_abc", max_results=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_result_structure(self, indexer):
        searcher = SemanticSearcher(indexer)
        results = await searcher.search("users", top_k=1, score_threshold=0.0)
        if results:
            r = results[0]
            assert r.file_path
            assert r.content
            assert 0 <= r.score <= 1.0
