import json
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ContextBudget:
    global_max: int = 2000
    task_max: int = 1500
    retrieved_max: int = 3000
    memory_max: int = 1500
    total_max: int = 8000


class ContextManager:
    """
    Assembles structured context for the AI agent with token budget awareness.

    Four-layer context model:
    1. Global — coding standards, architecture rules (highest priority)
    2. Task — current task description and derived constraints
    3. Retrieved — RAG-retrieved code snippets via vector search
    4. Memory — similar past tasks and their solutions
    """

    def __init__(
        self,
        vector_db_client=None,
        max_tokens: int = 8000,
        embedding_model: str = "text-embedding-3-large",
    ):
        self.vector_db = vector_db_client
        self.max_tokens = max_tokens
        self.embedding_model = embedding_model
        self.budget = ContextBudget(total_max=max_tokens)
        self.memory_cache: Dict[str, list] = {}
        self.global_rules = self._build_global_rules()

    def _build_global_rules(self) -> dict:
        return {
            "project": {
                "name": "FastAPI-Vite-Harness",
                "version": "1.0.0",
                "description": "AI-assisted web application development",
            },
            "architecture": {
                "backend_framework": "FastAPI",
                "frontend_framework": "React + Vite",
                "api_pattern": "REST + WebSocket for real-time",
                "db_pattern": "SQLAlchemy async + Alembic migrations",
                "security": "OAuth2 + RBAC, no secrets in code",
                "testing": "pytest backend, vitest frontend",
                "coverage_target": "80% minimum",
            },
            "coding_standards": {
                "python": {
                    "style": "PEP8",
                    "typing": "Mandatory type hints",
                    "async": "async/await for all I/O operations",
                    "imports": "isort + absolute imports",
                    "docstrings": "Google style, all public APIs",
                },
                "typescript": {
                    "mode": "Strict mode enabled",
                    "components": "Functional components with hooks",
                    "validation": "Zod for all API inputs",
                    "state": "Zustand for global, React Query for server",
                },
            },
            "forbidden_patterns": [
                {
                    "pattern": "No raw SQL without parameterization",
                    "severity": "CRITICAL",
                    "rationale": "SQL injection prevention",
                },
                {
                    "pattern": "No eval() or exec() in any context",
                    "severity": "CRITICAL",
                    "rationale": "Code injection prevention",
                },
                {
                    "pattern": "No hardcoded credentials",
                    "severity": "CRITICAL",
                    "rationale": "Secret management compliance",
                },
                {
                    "pattern": "No blocking I/O in async functions",
                    "severity": "HIGH",
                    "rationale": "Performance and deadlock prevention",
                },
                {
                    "pattern": "No circular imports",
                    "severity": "MEDIUM",
                    "rationale": "Maintainability",
                },
            ],
            "api_conventions": {
                "rest": {
                    "versioning": "URL path (/api/v1/...)",
                    "pagination": "Cursor-based for large datasets",
                    "errors": "RFC 7807 Problem Details",
                    "auth": "Bearer JWT in Authorization header",
                },
                "websocket": {
                    "protocol": "JSON messages",
                    "heartbeat": "30-second ping/pong",
                    "reconnection": "Exponential backoff",
                },
            },
        }

    _SCOPE_KEYWORDS: Dict[str, List[str]] = {
        "api": ["endpoint", "route", "handler", "fastapi", "api", "rest"],
        "ui": ["component", "page", "react", "vite", "frontend", "css", "html"],
        "db": ["migration", "model", "schema", "sqlalchemy", "database", "table"],
        "infra": ["docker", "deploy", "config", "ci/cd", "kubernetes", "terraform"],
        "test": ["test", "pytest", "vitest", "coverage", "mock"],
        "security": ["auth", "oauth", "jwt", "permission", "rbac", "encrypt"],
    }

    def build_context(
        self,
        task_description: str,
        relevant_files: Optional[List[str]] = None,
        task_scope: Optional[str] = None,
    ) -> dict:
        scope = task_scope or self._determine_scope(task_description)

        context: dict = {
            "version": "harness_context_v2",
            "scope": scope,
            "budget": {
                "total_max": self.budget.total_max,
                "allocated": 0,
                "remaining": self.budget.total_max,
            },
            "layers": {},
        }

        global_ctx = self._build_global_context(scope)
        context["layers"]["global"] = global_ctx
        context["budget"]["allocated"] += global_ctx["token_estimate"]

        task_ctx = self._build_task_context(task_description, scope)
        context["layers"]["task"] = task_ctx
        context["budget"]["allocated"] += task_ctx["token_estimate"]

        remaining = self.budget.total_max - context["budget"]["allocated"]
        retrieved_ctx = self._build_retrieved_context(
            task_description,
            relevant_files,
            max_tokens=min(self.budget.retrieved_max, int(remaining * 0.6)),
        )
        context["layers"]["retrieved"] = retrieved_ctx
        context["budget"]["allocated"] += retrieved_ctx["token_estimate"]

        remaining = self.budget.total_max - context["budget"]["allocated"]
        memory_ctx = self._build_memory_context(
            task_description,
            max_tokens=min(self.budget.memory_max, int(remaining * 0.8)),
        )
        context["layers"]["memory"] = memory_ctx
        context["budget"]["allocated"] += memory_ctx["token_estimate"]

        context["budget"]["remaining"] = (
            self.budget.total_max - context["budget"]["allocated"]
        )

        return context

    def _determine_scope(self, task: str) -> str:
        task_lower = task.lower()
        scores = {
            scope: sum(1 for kw in keywords if kw in task_lower)
            for scope, keywords in self._SCOPE_KEYWORDS.items()
        }
        best = max(scores, key=scores.get)  # type: ignore[type-var]
        return best if scores[best] > 0 else "general"

    def _build_global_context(self, scope: str) -> dict:
        rules = self.global_rules.copy()

        if scope == "api":
            rules["coding_standards"] = {
                "python": rules["coding_standards"]["python"]
            }
            rules["api_conventions"] = rules.get("api_conventions", {})
        elif scope == "ui":
            rules["coding_standards"] = {
                "typescript": rules["coding_standards"]["typescript"]
            }

        content = json.dumps(rules, indent=2)
        return {
            "content": rules,
            "token_estimate": len(content) // 4,
            "priority": "critical",
            "scope_filter": scope,
        }

    def _build_task_context(self, description: str, scope: str) -> dict:
        task_ctx = {
            "description": description,
            "scope": scope,
            "constraints": self._extract_constraints(description),
            "expected_outputs": self._infer_outputs(description, scope),
        }
        content = json.dumps(task_ctx, indent=2)
        return {
            "content": task_ctx,
            "token_estimate": len(content) // 4,
            "priority": "high",
        }

    def _build_retrieved_context(
        self,
        query: str,
        file_filter: Optional[List[str]] = None,
        max_tokens: int = 3000,
    ) -> dict:
        if not self.vector_db:
            return {"content": [], "token_estimate": 0, "priority": "medium"}

        results = self.vector_db.similarity_search(
            query=query,
            filter={"file_path": {"$in": file_filter}} if file_filter else None,
            top_k=5,
            score_threshold=0.7,
        )

        snippets: list = []
        total_tokens = 0

        for result in results:
            snippet_tokens = len(result["content"]) // 4
            if total_tokens + snippet_tokens > max_tokens:
                break
            snippets.append(
                {
                    "file_path": result["metadata"]["file_path"],
                    "content": result["content"],
                    "relevance_score": result["score"],
                    "lines": result["metadata"].get("line_range"),
                }
            )
            total_tokens += snippet_tokens

        return {
            "content": snippets,
            "token_estimate": total_tokens,
            "priority": "medium",
            "retrieval_method": "semantic_search",
        }

    def _build_memory_context(self, query: str, max_tokens: int = 1500) -> dict:
        if not self.vector_db:
            return {"content": [], "token_estimate": 0, "priority": "low"}

        memories = self.vector_db.similarity_search(
            query=query,
            collection="task_memory",
            top_k=3,
            score_threshold=0.8,
        )

        return {
            "content": [
                {
                    "task": m["metadata"]["original_task"],
                    "solution_summary": m["metadata"]["solution_summary"],
                    "success_rate": m["metadata"].get("success_rate", 0),
                    "relevance_score": m["score"],
                }
                for m in memories
            ],
            "token_estimate": sum(len(m["content"]) for m in memories) // 4,
            "priority": "low",
        }

    def _extract_constraints(self, description: str) -> list:
        constraints = []
        d = description.lower()
        if "async" in d:
            constraints.append("Must use async/await pattern")
        if "test" in d:
            constraints.append("Must include unit tests")
        if "api" in d:
            constraints.append("Must follow OpenAPI schema")
        return constraints

    def _infer_outputs(self, description: str, scope: str) -> list:
        if scope == "api":
            return ["FastAPI endpoint", "Pydantic models", "Tests"]
        if scope == "ui":
            return ["React component", "TypeScript types", "Storybook story"]
        if scope == "db":
            return ["SQLAlchemy model", "Alembic migration", "Tests"]
        return ["Implementation code", "Tests"]
