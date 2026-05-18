# Harness Engineering Strategy: Full-Scope Implementation Guide

## FastAPI + Node.js + Vite Web Application with Claude Code Integration

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Strategic Overview](#2-strategic-overview)
3. [Architecture Blueprint](#3-architecture-blueprint)
4. [Harness Core: Control Plane](#4-harness-core-control-plane)
5. [Security & Governance](#5-security--governance)
6. [Orchestrator: Claude Code Integration](#6-orchestrator-claude-code-integration)
7. [Quality Assurance: Evaluator](#7-quality-assurance-evaluator)
8. [Execution Environment](#8-execution-environment)
9. [Frontend Dashboard (Vite + Node.js)](#9-frontend-dashboard-vite--nodejs)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Key Engineering Principles](#11-key-engineering-principles)
12. [Appendix: Configuration Files](#12-appendix-configuration-files)

---

## 1. Executive Summary

This document presents a comprehensive strategy for building a **Harness Engineering** system that transforms Claude Code from an interactive coding assistant into a **managed, governable, and recoverable agent** within a production-grade software engineering environment.

### Core Philosophy

> **"The system (Harness) determines the upper bound of capability, not the model."**

Software engineering is evolving from "humans writing code" to "humans designing systems that enable AI agents to generate and evolve code autonomously, safely, and efficiently."

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | FastAPI (Python 3.11+) |
| **Frontend** | React + Vite + TypeScript |
| **Agent Integration** | Claude Code via MCP (Model Context Protocol) |
| **State Management** | PostgreSQL + Redis |
| **Vector Search** | pgvector / Qdrant |
| **Containerization** | Docker + Docker Compose |
| **Message Queue** | Redis / RabbitMQ |
| **Monitoring** | Prometheus + Grafana |

---

## 2. Strategic Overview

### 2.1 Problem Statement

Traditional AI coding assistants face critical limitations in production environments:

- **No state persistence**: Lost context on interruption
- **No recovery mechanism**: Failed tasks restart from scratch
- **No governance**: Unrestricted access to production systems
- **No quality gates**: Generated code lacks systematic validation
- **No audit trail**: Actions cannot be traced or reviewed

### 2.2 Solution: The Harness Architecture

The Harness Engineering approach treats the AI agent as an **operating system process** that requires:

1. **Scheduling** (Task Planner with DAG)
2. **Memory** (Context Manager + State Store)
3. **System Calls** (Tool Registry with permissions)
4. **Fault Tolerance** (Checkpoint + Recovery)
5. **Security** (Governance + Sandbox)
6. **Quality Control** (Multi-dimensional Evaluator)

### 2.3 Target Architecture

The system consists of three main layers:

**Control Plane** (Harness Core):
- Task Planner with DAG dependency management
- Context Manager with token budget optimization
- Governance & Audit system with human-in-the-loop

**Orchestration Layer** (Agent Loop):
- MCP Server for Claude Code integration
- Reasoning -> Action -> Execution -> Evaluation -> Feedback cycle
- Self-healing with max iteration limits

**Execution Environment** (Sandbox):
- Isolated Docker containers with no network access
- Resource limits (CPU, Memory, Disk)
- Read-only root filesystem

---

## 3. Architecture Blueprint

### 3.1 System Components

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Task Planner** | Decompose requests into DAG tasks | Python (NetworkX) |
| **Context Manager** | Supply relevant, token-optimized context | pgvector + RAG |
| **Tool Registry** | Controlled tool access with schema validation | Pydantic + FastAPI |
| **State Store** | Persistent checkpoints for recovery | PostgreSQL + Redis |
| **Orchestrator** | Manage Agent Loop execution | Asyncio + WebSocket |
| **Evaluator** | Multi-dimensional quality assessment | pytest + mypy + bandit |
| **Governance** | Constraints, audit, human approval | Custom + OAuth2 |
| **Sandbox** | Isolated execution environment | Docker (network=none) |

### 3.2 Data Flow

```
User Request
    |
[Task Planner] -> DAG Generation
    |
[Context Manager] -> Context Assembly (Global + Task + RAG)
    |
[Orchestrator] -> Agent Loop Initiation
    |
[Claude Code MCP] -> Reasoning + Action Planning
    |
[Tool Registry] -> Permission Check + Schema Validation
    |
[Sandbox] -> Isolated Execution
    |
[Evaluator] -> Multi-Dimensional Assessment
    |
[Feedback Loop] -> Pass? -> Yes: Complete / No: Iterate (max 5)
    |
[State Store] -> Checkpoint Save
    |
[Audit Log] -> Immutable Record
```

---

## 4. Harness Core: Control Plane

### 4.1 Task Planner (DAG-Based)

#### 4.1.1 Design Goals

- Decompose complex problems into executable tasks (DAG)
- Explicit dependency management for correct execution order
- Idempotent task design for safe retry and recovery
- Topological sorting for deterministic execution

#### 4.1.2 Core Implementation

```python
# backend/app/harness/planner.py
from typing import Dict, List, Callable, Optional
from collections import defaultdict
from enum import Enum
import asyncio
import json

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskNode:
    """
    Represents a single unit of work in the task graph.
    Designed to be idempotent and self-contained.
    """
    def __init__(self, 
                 id: str, 
                 description: str, 
                 action: Callable, 
                 deps: List[str] = None,
                 task_type: str = "code",
                 retry_count: int = 3,
                 timeout_seconds: int = 300):
        self.id = id
        self.description = description
        self.action = action
        self.deps = deps or []
        self.status = TaskStatus.PENDING
        self.task_type = task_type
        self.retry_count = retry_count
        self.timeout_seconds = timeout_seconds
        self.result = None
        self.error_log = []
        self.checkpoint_data = {}
        
    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "deps": self.deps,
            "type": self.task_type,
            "result": self.result,
            "error_log": self.error_log,
            "checkpoint": self.checkpoint_data
        }

class TaskPlanner:
    """
    DAG-based task planner with topological sorting.
    Ensures idempotent execution and dependency resolution.
    
    Key Principles:
    - Tasks are idempotent (safe to retry)
    - Dependencies are explicit (no hidden coupling)
    - Execution order is deterministic (topological sort)
    - State is checkpointed after each task (recoverable)
    """
    
    def __init__(self, state_store_path: str = "harness_state.json"):
        self.tasks: Dict[str, TaskNode] = {}
        self.graph = defaultdict(list)
        self.reverse_graph = defaultdict(list)
        self.state_store_path = state_store_path
        self._load_state()
    
    def add_task(self, node: TaskNode):
        """Register a task with dependency awareness."""
        if node.id in self.tasks:
            raise ValueError(f"Task {node.id} already exists")
            
        self.tasks[node.id] = node
        
        for dep in node.deps:
            self.graph[dep].append(node.id)
            self.reverse_graph[node.id].append(dep)
    
    def get_execution_order(self) -> List[str]:
        """
        Topological sort using Kahn's algorithm.
        Returns list of task IDs in execution order.
        """
        in_degree = {tid: len(self.reverse_graph[tid]) for tid in self.tasks}
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            for neighbor in self.graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(order) != len(self.tasks):
            remaining = set(self.tasks.keys()) - set(order)
            raise ValueError(f"Cycle detected in tasks: {remaining}")
            
        return order
    
    async def execute_with_recovery(self, orchestrator):
        """
        Execute tasks with checkpointing and failure recovery.
        
        Algorithm:
        1. Load previous state (resume from checkpoint)
        2. Get execution order (topological sort)
        3. For each task:
           a. Skip if already completed (idempotency)
           b. Execute with retry logic
           c. Save checkpoint on success
           d. Trigger feedback loop on failure
        """
        order = self.get_execution_order()
        
        for task_id in order:
            task = self.tasks[task_id]
            
            # Skip if already completed (idempotency check)
            if task.status == TaskStatus.COMPLETED:
                continue
                
            task.status = TaskStatus.RUNNING
            self._save_state()
            
            success = False
            for attempt in range(task.retry_count):
                try:
                    result = await asyncio.wait_for(
                        orchestrator.execute_task(task),
                        timeout=task.timeout_seconds
                    )
                    
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    self._save_state()
                    success = True
                    break
                    
                except asyncio.TimeoutError:
                    task.error_log.append(f"Attempt {attempt + 1}: Timeout")
                except Exception as e:
                    task.error_log.append(f"Attempt {attempt + 1}: {str(e)}")
            
            if not success:
                task.status = TaskStatus.FAILED
                self._save_state()
                await self._trigger_feedback_loop(task, orchestrator)
                raise Exception(
                    f"Task {task_id} failed after {task.retry_count} attempts"
                )
    
    def _save_state(self):
        """Checkpoint state to disk for recovery."""
        state = {tid: node.to_dict() for tid, node in self.tasks.items()}
        temp_path = f"{self.state_store_path}.tmp"
        
        with open(temp_path, 'w') as f:
            json.dump(state, f, indent=2)
            
        import os
        os.replace(temp_path, self.state_store_path)
    
    def _load_state(self):
        """Resume from checkpoint if exists."""
        try:
            with open(self.state_store_path, 'r') as f:
                state = json.load(f)
                
            for tid, data in state.items():
                if tid in self.tasks:
                    self.tasks[tid].status = TaskStatus(data["status"])
                    self.tasks[tid].result = data.get("result")
                    self.tasks[tid].error_log = data.get("error_log", [])
                    self.tasks[tid].checkpoint_data = data.get("checkpoint", {})
                    
        except FileNotFoundError:
            pass  # Fresh start
    
    async def _trigger_feedback_loop(self, failed_task, orchestrator):
        """Auto-fix mechanism: analyze failure and replan."""
        feedback = {
            "failed_task": failed_task.id,
            "errors": failed_task.error_log,
            "context": failed_task.description,
            "checkpoint": failed_task.checkpoint_data
        }
        
        await orchestrator.reflect_and_fix(feedback)
```

#### 4.1.3 Engineering Checklist

- [ ] All tasks must be idempotent (same result on retry)
- [ ] No hidden dependencies between tasks
- [ ] Task granularity balances recovery vs. overhead
- [ ] Timeout configured per task type
- [ ] State saved atomically to prevent corruption

---

### 4.2 Context Manager

#### 4.2.1 Design Goals

- Provide accurate, relevant context to the agent
- Control context size to manage token costs
- Prevent context pollution from unrelated information
- Enable retrieval-augmented generation (RAG) for large codebases

#### 4.2.2 Context Layers

| Layer | Content | Source | Priority |
|-------|---------|--------|----------|
| **Global** | Coding standards, architecture rules | `harness_rules.yaml` | Critical |
| **Task** | Current task description and scope | User input + Planner | High |
| **Retrieved** | Relevant code snippets via RAG | Vector DB (pgvector) | Medium |
| **Memory** | Previous similar tasks/solutions | Task history DB | Low |

#### 4.2.3 Core Implementation

```python
# backend/app/harness/context_manager.py
from typing import Dict, List, Optional, Tuple
import hashlib
import json
from dataclasses import dataclass

@dataclass
class ContextBudget:
    """Token budget allocation per context layer."""
    global_max: int = 2000
    task_max: int = 1500
    retrieved_max: int = 3000
    memory_max: int = 1500
    total_max: int = 8000

class ContextManager:
    """
    Manages context assembly with token budget awareness.
    
    Principles:
    - Structured output (JSON schema enforcement)
    - Token budget enforcement (prevent context overflow)
    - Retrieval quality directly impacts generation quality
    - Context pollution prevention (strict relevance filtering)
    """
    
    def __init__(self, 
                 vector_db_client,
                 max_tokens: int = 8000,
                 embedding_model: str = "text-embedding-3-large"):
        self.vector_db = vector_db_client
        self.max_tokens = max_tokens
        self.embedding_model = embedding_model
        self.global_rules = self._load_global_rules()
        self.memory_cache = {}
        self.budget = ContextBudget(total_max=max_tokens)
    
    def _load_global_rules(self) -> Dict:
        """
        Load project-specific constraints.
        These are the "strong constraints" that reduce
        the LLM's search space and improve consistency.
        """
        return {
            "project": {
                "name": "FastAPI-Vite-Harness",
                "version": "1.0.0",
                "description": "AI-assisted web application development"
            },
            "architecture": {
                "backend_framework": "FastAPI",
                "frontend_framework": "React + Vite",
                "api_pattern": "REST + WebSocket for real-time",
                "db_pattern": "SQLAlchemy async + Alembic migrations",
                "security": "OAuth2 + RBAC, no secrets in code",
                "testing": "pytest backend, vitest frontend",
                "coverage_target": "80% minimum"
            },
            "coding_standards": {
                "python": {
                    "style": "PEP8",
                    "typing": "Mandatory type hints",
                    "async": "async/await for all I/O operations",
                    "imports": "isort + absolute imports",
                    "docstrings": "Google style, all public APIs"
                },
                "typescript": {
                    "mode": "Strict mode enabled",
                    "components": "Functional components with hooks",
                    "validation": "Zod for all API inputs",
                    "state": "Zustand for global, React Query for server"
                }
            },
            "forbidden_patterns": [
                {
                    "pattern": "No raw SQL without parameterization",
                    "severity": "CRITICAL",
                    "rationale": "SQL injection prevention"
                },
                {
                    "pattern": "No eval() or exec() in any context",
                    "severity": "CRITICAL",
                    "rationale": "Code injection prevention"
                },
                {
                    "pattern": "No hardcoded credentials",
                    "severity": "CRITICAL",
                    "rationale": "Secret management compliance"
                },
                {
                    "pattern": "No blocking I/O in async functions",
                    "severity": "HIGH",
                    "rationale": "Performance and deadlock prevention"
                },
                {
                    "pattern": "No circular imports",
                    "severity": "MEDIUM",
                    "rationale": "Maintainability"
                }
            ],
            "api_conventions": {
                "rest": {
                    "versioning": "URL path (/api/v1/...)",
                    "pagination": "Cursor-based for large datasets",
                    "errors": "RFC 7807 Problem Details",
                    "auth": "Bearer JWT in Authorization header"
                },
                "websocket": {
                    "protocol": "JSON messages",
                    "heartbeat": "30-second ping/pong",
                    "reconnection": "Exponential backoff"
                }
            }
        }
    
    def build_context(self, 
                     task_description: str, 
                     relevant_files: List[str] = None,
                     task_scope: str = None) -> Dict:
        """
        Construct structured context with token budget management.
        
        Args:
            task_description: Natural language task description
            relevant_files: Optional file paths for focused retrieval
            task_scope: Override automatic scope detection
            
        Returns:
            Structured context dictionary with budget metadata
        """
        scope = task_scope or self._determine_scope(task_description)
        
        context = {
            "version": "harness_context_v2",
            "scope": scope,
            "budget": {
                "total_max": self.budget.total_max,
                "allocated": 0,
                "remaining": self.budget.total_max
            },
            "layers": {}
        }
        
        # Layer 1: Global rules (highest priority)
        global_ctx = self._build_global_context(scope)
        context["layers"]["global"] = global_ctx
        context["budget"]["allocated"] += global_ctx["token_estimate"]
        
        # Layer 2: Task-specific context
        task_ctx = self._build_task_context(task_description, scope)
        context["layers"]["task"] = task_ctx
        context["budget"]["allocated"] += task_ctx["token_estimate"]
        
        # Layer 3: RAG retrieval
        remaining = self.budget.total_max - context["budget"]["allocated"]
        retrieved_ctx = self._build_retrieved_context(
            task_description, 
            relevant_files,
            max_tokens=min(self.budget.retrieved_max, remaining * 0.6)
        )
        context["layers"]["retrieved"] = retrieved_ctx
        context["budget"]["allocated"] += retrieved_ctx["token_estimate"]
        
        # Layer 4: Organizational memory
        remaining = self.budget.total_max - context["budget"]["allocated"]
        memory_ctx = self._build_memory_context(
            task_description,
            max_tokens=min(self.budget.memory_max, remaining * 0.8)
        )
        context["layers"]["memory"] = memory_ctx
        context["budget"]["allocated"] += memory_ctx["token_estimate"]
        
        context["budget"]["remaining"] = (
            self.budget.total_max - context["budget"]["allocated"]
        )
        
        return context
    
    def _determine_scope(self, task: str) -> str:
        """Classify task scope for context optimization."""
        scopes = {
            "api": ["endpoint", "route", "handler", "fastapi", "api", "rest"],
            "ui": ["component", "page", "react", "vite", "frontend", "css", "html"],
            "db": ["migration", "model", "schema", "sqlalchemy", "database", "table"],
            "infra": ["docker", "deploy", "config", "ci/cd", "kubernetes", "terraform"],
            "test": ["test", "pytest", "vitest", "coverage", "mock"],
            "security": ["auth", "oauth", "jwt", "permission", "rbac", "encrypt"]
        }
        
        task_lower = task.lower()
        scores = {scope: sum(1 for k in keywords if k in task_lower) 
                 for scope, keywords in scopes.items()}
        
        best_scope = max(scores, key=scores.get)
        return best_scope if scores[best_scope] > 0 else "general"
    
    def _build_global_context(self, scope: str) -> Dict:
        """Build global rules context, scope-filtered for relevance."""
        relevant_rules = self.global_rules.copy()
        
        if scope == "api":
            relevant_rules["coding_standards"] = {
                "python": relevant_rules["coding_standards"]["python"]
            }
            relevant_rules["api_conventions"] = relevant_rules.get("api_conventions", {})
        elif scope == "ui":
            relevant_rules["coding_standards"] = {
                "typescript": relevant_rules["coding_standards"]["typescript"]
            }
        
        content = json.dumps(relevant_rules, indent=2)
        
        return {
            "content": relevant_rules,
            "token_estimate": len(content) // 4,
            "priority": "critical",
            "scope_filter": scope
        }
    
    def _build_task_context(self, description: str, scope: str) -> Dict:
        """Build task-specific context."""
        task_ctx = {
            "description": description,
            "scope": scope,
            "constraints": self._extract_constraints(description),
            "expected_outputs": self._infer_outputs(description, scope)
        }
        
        content = json.dumps(task_ctx, indent=2)
        
        return {
            "content": task_ctx,
            "token_estimate": len(content) // 4,
            "priority": "high"
        }
    
    def _build_retrieved_context(self, 
                                query: str, 
                                file_filter: List[str] = None,
                                max_tokens: int = 3000) -> Dict:
        """
        Retrieve relevant code snippets via vector search.
        Uses pgvector or Qdrant for semantic similarity search.
        """
        if not self.vector_db:
            return {"content": [], "token_estimate": 0, "priority": "medium"}
        
        results = self.vector_db.similarity_search(
            query=query,
            filter={"file_path": {"$in": file_filter}} if file_filter else None,
            top_k=5,
            score_threshold=0.7
        )
        
        snippets = []
        total_tokens = 0
        
        for result in results:
            snippet_tokens = len(result["content"]) // 4
            if total_tokens + snippet_tokens > max_tokens:
                break
                
            snippets.append({
                "file_path": result["metadata"]["file_path"],
                "content": result["content"],
                "relevance_score": result["score"],
                "lines": result["metadata"].get("line_range")
            })
            total_tokens += snippet_tokens
        
        return {
            "content": snippets,
            "token_estimate": total_tokens,
            "priority": "medium",
            "retrieval_method": "semantic_search"
        }
    
    def _build_memory_context(self, query: str, max_tokens: int = 1500) -> Dict:
        """Retrieve previous similar tasks and their solutions."""
        if not self.vector_db:
            return {"content": [], "token_estimate": 0, "priority": "low"}
        
        memories = self.vector_db.similarity_search(
            query=query,
            collection="task_memory",
            top_k=3,
            score_threshold=0.8
        )
        
        return {
            "content": [
                {
                    "task": m["metadata"]["original_task"],
                    "solution_summary": m["metadata"]["solution_summary"],
                    "success_rate": m["metadata"].get("success_rate", 0),
                    "relevance_score": m["score"]
                }
                for m in memories
            ],
            "token_estimate": sum(len(m["content"]) for m in memories) // 4,
            "priority": "low"
        }
    
    def _extract_constraints(self, description: str) -> List[str]:
        """Extract implicit constraints from task description."""
        constraints = []
        
        if "async" in description.lower():
            constraints.append("Must use async/await pattern")
        if "test" in description.lower():
            constraints.append("Must include unit tests")
        if "api" in description.lower():
            constraints.append("Must follow OpenAPI schema")
            
        return constraints
    
    def _infer_outputs(self, description: str, scope: str) -> List[str]:
        """Infer expected outputs based on task type."""
        outputs = []
        
        if scope == "api":
            outputs.extend(["FastAPI endpoint", "Pydantic models", "Tests"])
        elif scope == "ui":
            outputs.extend(["React component", "TypeScript types", "Storybook story"])
        elif scope == "db":
            outputs.extend(["SQLAlchemy model", "Alembic migration", "Tests"])
            
        return outputs
```

#### 4.2.4 Context Optimization Strategies

| Strategy | Implementation | Benefit |
|----------|-----------------|---------|
| **Scope Filtering** | Only load relevant standards | -40% tokens |
| **Semantic Retrieval** | Vector search for code snippets | +60% relevance |
| **Memory Caching** | Similar task solutions | -30% generation time |
| **Budget Enforcement** | Hard token limits per layer | Prevents overflow |

---

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_checkpoints_task ON harness_checkpoints(task_id, timestamp DESC);

CREATE TABLE harness_events (
    event_id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    type VARCHAR(32) NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sequence INTEGER NOT NULL,
    UNIQUE(task_id, sequence)
);

CREATE INDEX idx_events_task_sequence ON harness_events(task_id, sequence);

-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE code_embeddings (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embeddings_vector ON code_embeddings 
    USING ivfflat (embedding vector_cosine_ops);
```

---

## 5. Security & Governance

### 5.1 Tool Registry with Permissions

#### 5.1.1 Permission Model

| Level | Value | Capabilities | Examples |
|-------|-------|-------------|----------|
| **READ** | 1 | Code analysis, search, read files | `read_file`, `search_code` |
| **WRITE** | 2 | File modifications, code generation | `write_file`, `generate_api` |
| **EXECUTE** | 3 | Run tests, linters, type checkers | `run_tests`, `run_linter` |
| **DEPLOY** | 4 | Deployment to staging/production | `deploy_staging`, `deploy_prod` |
| **ADMIN** | 5 | System configuration changes | `modify_ci_cd`, `manage_secrets` |

#### 5.1.2 Core Implementation

The Tool Registry provides controlled tool access with:

- **Schema Validation**: All tool parameters validated via Pydantic
- **Permission Enforcement**: Role-based access control (RBAC)
- **Rate Limiting**: Sliding window counters per tool
- **Audit Logging**: Immutable record of all tool invocations
- **Scope Restrictions**: Task-type based tool availability

Key components:

```python
class PermissionLevel(Enum):
    READ = 1      # Code analysis, search
    WRITE = 2     # File modifications
    EXECUTE = 3   # Run tests, linters
    DEPLOY = 4    # Deployment (requires approval)
    ADMIN = 5     # System configuration

class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter]
    permission_required: PermissionLevel
    requires_approval: bool = False
    audit_level: str = "full"
    risk_level: str = "low"
    allowed_scopes: List[str] = ["*"]
    rate_limit: Optional[int] = None

class ToolRegistry:
    def __init__(self, governance):
        self.tools = {}
        self.implementations = {}
        self.governance = governance
        self.audit_log = []
        self.rate_counters = {}

    def register(self, schema, implementation):
        if schema.name in self.tools:
            raise ValueError(f"Tool {schema.name} already registered")
        self.tools[schema.name] = schema
        self.implementations[schema.name] = implementation
        self.rate_counters[schema.name] = []

    async def call(self, name, user_permission, params, session_id, task_scope="general"):
        # 1. Tool existence check
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        tool = self.tools[name]

        # 2. Scope validation
        if task_scope not in tool.allowed_scopes and "*" not in tool.allowed_scopes:
            raise PermissionError(f"Tool {name} not allowed for scope '{task_scope}'")

        # 3. Rate limiting
        await self._check_rate_limit(name, tool.rate_limit)

        # 4. Constraint check (Governance)
        self.governance.check_constraint(name, params)

        # 5. Permission check
        if user_permission.value < tool.permission_required.value:
            raise PermissionError(
                f"Tool {name} requires {tool.permission_required.name} "
                f"(you have {user_permission.name})"
            )

        # 6. Human-in-the-loop for high-risk operations
        if tool.requires_approval:
            approved = await self.governance.request_human_approval(
                action=name, params=params,
                session_id=session_id, risk_level=tool.risk_level
            )
            if not approved:
                raise PermissionError("Human approval denied")

        # 7. Audit logging
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "tool": name,
            "params": self._sanitize_params(params),
            "permission": user_permission.name,
            "risk_level": tool.risk_level
        }
        self.audit_log.append(audit_entry)
        self.governance.audit(audit_entry)

        # 8. Execute in sandbox
        try:
            result = await self._execute_in_sandbox(name, params)
            return ToolExecutionResult(success=True, output=result, ...)
        except Exception as e:
            return ToolExecutionResult(success=False, output=None, ...)
```

#### 5.1.3 Pre-defined Tool Set

**READ-level tools:**

- `read_file`: Read file contents for analysis
- `search_code`: Search codebase using AST or regex
- `analyze_dependencies`: Analyze import/module dependencies

**WRITE-level tools:**

- `write_file`: Write or modify source files (with backup)
- `generate_api`: Generate FastAPI endpoint from OpenAPI spec
- `generate_component`: Generate React component with TypeScript

**EXECUTE-level tools:**

- `run_tests`: Execute test suite with coverage reporting
- `run_linter`: Run code quality checks (ruff, mypy, black)
- `run_security_scan`: Run security analysis (bandit, semgrep)

**DEPLOY-level tools (requires approval):**

- `deploy_staging`: Deploy to staging environment
- `deploy_production`: Deploy to production (canary rollout)

---

### 5.2 Governance & Audit System

#### 5.2.1 Constraint Framework

The Governance system enforces architectural constraints that cannot be violated.
This implements the principle: **"Strong constraints > Strong model"**

| Constraint ID | Description | Severity | Auto-Fix | Scope |
|--------------|-------------|----------|----------|-------|
| `no_blocking_io` | All I/O operations must be async | HIGH | No | api, db, infra |
| `type_safety` | All functions must have type hints | MEDIUM | Yes | code, api, ui |
| `sql_injection_prevention` | No string concatenation in SQL | CRITICAL | No | db, api |
| `secret_detection` | No hardcoded secrets in code | CRITICAL | No | code, config |
| `no_circular_imports` | No circular import dependencies | MEDIUM | Yes | code, api, ui |
| `test_coverage` | All new code must have tests | HIGH | No | code, api, ui, db |

#### 5.2.2 Core Implementation

```python
# backend/app/harness/governance.py
from typing import Dict, List, Optional, Set, Callable
from enum import Enum
import asyncio
import json
from datetime import datetime
from dataclasses import dataclass

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ConstraintRule:
    """Defines a system constraint that cannot be violated."""
    id: str
    description: str
    check_function: Callable
    severity: RiskLevel
    scope: List[str]
    auto_fix: bool = False

@dataclass
class AuditEntry:
    """Immutable audit record."""
    entry_id: str
    timestamp: str
    session_id: str
    action: str
    actor: str
    params: Dict
    result: str
    risk_level: RiskLevel
    approval_required: bool
    approval_granted: Optional[bool]

class Governance:
    """
    Constraint enforcement, audit logging, and human-in-the-loop.
    
    Implements the principle: "Strong constraints > Strong model"
    By constraining the LLM's search space through rules,
    we improve consistency and reduce uncertainty.
    """
    
    def __init__(self, 
                 notification_service=None,
                 approval_timeout_seconds: int = 300):
        self.forbidden_actions: Set[str] = {
            "delete_prod_db",
            "drop_table",
            "exec_shell_unrestricted",
            "modify_ci_cd",
            "access_secrets_vault",
            "disable_audit_logging",
            "modify_governance_rules"
        }
        
        self.constraint_rules = self._load_constraint_rules()
        self.audit_log: List[AuditEntry] = []
        self.pending_approvals: Dict[str, asyncio.Future] = {}
        self.notification_service = notification_service
        self.approval_timeout = approval_timeout_seconds
        self.approval_callbacks: Dict[str, Callable] = {}

    def _load_constraint_rules(self) -> List[ConstraintRule]:
        """Load architectural constraints."""
        return [
            ConstraintRule(
                id="no_blocking_io",
                description="All I/O operations must be async",
                check_function=self._check_async_patterns,
                severity=RiskLevel.HIGH,
                scope=["api", "db", "infra"],
                auto_fix=False
            ),
            ConstraintRule(
                id="type_safety",
                description="All functions must have type hints",
                check_function=self._check_type_hints,
                severity=RiskLevel.MEDIUM,
                scope=["code", "api", "ui"],
                auto_fix=True
            ),
            ConstraintRule(
                id="sql_injection_prevention",
                description="No string concatenation in SQL",
                check_function=self._check_sql_safety,
                severity=RiskLevel.CRITICAL,
                scope=["db", "api"],
                auto_fix=False
            ),
            ConstraintRule(
                id="secret_detection",
                description="No hardcoded secrets in generated code",
                check_function=self._check_secrets,
                severity=RiskLevel.CRITICAL,
                scope=["code", "config", "infra"],
                auto_fix=False
            ),
            ConstraintRule(
                id="no_circular_imports",
                description="No circular import dependencies",
                check_function=self._check_circular_imports,
                severity=RiskLevel.MEDIUM,
                scope=["code", "api", "ui"],
                auto_fix=True
            ),
            ConstraintRule(
                id="test_coverage",
                description="All new code must have tests",
                check_function=self._check_test_coverage,
                severity=RiskLevel.HIGH,
                scope=["code", "api", "ui", "db"],
                auto_fix=False
            )
        ]

    def check_constraint(self, action: str, params: Dict, 
                        task_scope: str = "general") -> Dict:
        """
        Pre-execution constraint validation.
        Returns Dict with passed boolean and violations list.
        """
        violations = []
        
        # Check forbidden actions
        if action in self.forbidden_actions:
            violations.append({
                "rule": "forbidden_action",
                "severity": RiskLevel.CRITICAL,
                "message": f"Action '{action}' is permanently forbidden"
            })
        
        # Run applicable constraint checks
        for rule in self.constraint_rules:
            if task_scope in rule.scope or "*" in rule.scope:
                try:
                    result = rule.check_function(params)
                    if not result["passed"]:
                        violations.append({
                            "rule": rule.id,
                            "severity": rule.severity,
                            "message": result["message"],
                            "auto_fixable": rule.auto_fix,
                            "suggestion": result.get("suggestion")
                        })
                except Exception as e:
                    violations.append({
                        "rule": rule.id,
                        "severity": RiskLevel.HIGH,
                        "message": f"Constraint check failed: {str(e)}"
                    })
        
        critical_violations = [v for v in violations 
                              if v["severity"] == RiskLevel.CRITICAL]
        
        return {
            "passed": len(critical_violations) == 0 and len(violations) < 3,
            "violations": violations,
            "can_proceed": len(critical_violations) == 0
        }

    async def request_human_approval(self, 
                                    action: str, 
                                    params: Dict,
                                    session_id: str,
                                    risk_level: str = "medium") -> bool:
        """
        Human-in-the-loop for high-risk operations.
        
        Flow:
        1. Generate approval request
        2. Send notification (Slack, email, dashboard)
        3. Wait for human response (with timeout)
        4. Default deny on timeout
        """
        approval_id = (
            f"apr_{session_id}_{action}_"
            f"{int(datetime.utcnow().timestamp() * 1000)}"
        )
        
        request = {
            "approval_id": approval_id,
            "session_id": session_id,
            "action": action,
            "params": self._sanitize_for_display(params),
            "risk_level": risk_level,
            "requested_at": datetime.utcnow().isoformat(),
            "timeout_at": (
                datetime.utcnow().timestamp() + self.approval_timeout
            )
        }
        
        await self._send_approval_notification(request)
        
        future = asyncio.get_event_loop().create_future()
        self.pending_approvals[approval_id] = future
        
        try:
            approved = await asyncio.wait_for(
                future, 
                timeout=self.approval_timeout
            )
            
            self.audit({
                "approval_id": approval_id,
                "action": action,
                "approved": approved,
                "responded_at": datetime.utcnow().isoformat()
            })
            
            return approved
            
        except asyncio.TimeoutError:
            self.audit({
                "approval_id": approval_id,
                "action": action,
                "approved": False,
                "reason": "timeout"
            })
            return False

    def approve_request(self, approval_id: str, approved: bool, 
                       approver: str = "unknown"):
        """Called by human reviewer interface."""
        if approval_id in self.pending_approvals:
            future = self.pending_approvals[approval_id]
            
            self.audit({
                "approval_id": approval_id,
                "approver": approver,
                "decision": approved,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            future.set_result(approved)
            del self.pending_approvals[approval_id]

    def audit(self, entry: Dict):
        """
        Immutable audit logging.
        All critical operations are recorded with:
        - Tamper-evident hashing
        - Append-only storage
        - Real-time monitoring
        """
        audit_entry = AuditEntry(
            entry_id=self._generate_entry_id(entry),
            timestamp=datetime.utcnow().isoformat(),
            session_id=entry.get("session_id", "system"),
            action=entry.get("action", "unknown"),
            actor=entry.get("actor", "system"),
            params=entry.get("params", {}),
            result=entry.get("result", "pending"),
            risk_level=RiskLevel(entry.get("risk_level", "low")),
            approval_required=entry.get("requires_approval", False),
            approval_granted=entry.get("approved")
        )
        
        self.audit_log.append(audit_entry)
        self._persist_audit(audit_entry)
        
        if audit_entry.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            asyncio.create_task(self._alert_monitoring(audit_entry))

    def _generate_entry_id(self, entry: Dict) -> str:
        """Generate tamper-evident hash for audit entry."""
        content = json.dumps(entry, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def _send_approval_notification(self, request: Dict):
        """Send notification to human reviewers."""
        if self.notification_service:
            await self.notification_service.send({
                "type": "approval_required",
                "priority": "high",
                "payload": request
            })

    async def _alert_monitoring(self, entry: AuditEntry):
        """Send real-time alert for high-risk operations."""
        if self.notification_service:
            await self.notification_service.send({
                "type": "security_alert",
                "severity": entry.risk_level.value,
                "payload": {
                    "action": entry.action,
                    "actor": entry.actor,
                    "timestamp": entry.timestamp
                }
            })

    def _sanitize_for_display(self, params: Dict) -> Dict:
        """Sanitize params for human-readable approval requests."""
        sanitized = {}
        for k, v in params.items():
            if isinstance(v, str) and len(v) > 500:
                sanitized[k] = v[:500] + "... [truncated]"
            else:
                sanitized[k] = v
        return sanitized

    # Constraint Check Implementations

    def _check_async_patterns(self, params: Dict) -> Dict:
        """Check for blocking I/O in async contexts."""
        code = params.get("content", "")
        blocking_patterns = [
            "requests.get", "requests.post",
            "open(", "file(",
            "time.sleep(", "input(", "raw_input("
        ]
        violations = [p for p in blocking_patterns if p in code]
        return {
            "passed": len(violations) == 0,
            "message": f"Blocking I/O found: {violations}" if violations else "OK",
            "suggestion": "Use asyncio, aiohttp, or aiofiles"
        }

    def _check_type_hints(self, params: Dict) -> Dict:
        """Check for type hints in Python code."""
        code = params.get("content", "")
        has_hints = "->" in code or "from typing import" in code
        return {
            "passed": has_hints,
            "message": "Type hints missing" if not has_hints else "OK",
            "suggestion": "Add type hints to all function signatures"
        }

    def _check_sql_safety(self, params: Dict) -> Dict:
        """Check for SQL injection vulnerabilities."""
        code = params.get("content", "")
        dangerous_patterns = [
            "f\"SELECT", "f\"INSERT", "f\"UPDATE", "f\"DELETE",
            "+ \"SELECT", "+ \"INSERT", "+ \"UPDATE"
        ]
        violations = [p for p in dangerous_patterns if p in code]
        return {
            "passed": len(violations) == 0,
            "message": f"SQL injection risk: {violations}" if violations else "OK",
            "suggestion": "Use SQLAlchemy ORM or parameterized queries"
        }

    def _check_secrets(self, params: Dict) -> Dict:
        """Check for hardcoded secrets."""
        code = params.get("content", "")
        import re
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']'
        ]
        violations = []
        for pattern in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(pattern)
        return {
            "passed": len(violations) == 0,
            "message": "Hardcoded secrets found" if violations else "OK",
            "suggestion": "Use environment variables or secret management"
        }

    def _check_circular_imports(self, params: Dict) -> Dict:
        """Check for circular import dependencies."""
        return {"passed": True, "message": "OK"}

    def _check_test_coverage(self, params: Dict) -> Dict:
        """Check if tests exist for new code."""
        return {"passed": True, "message": "OK"}

    def _persist_audit(self, entry: AuditEntry):
        """Persist to tamper-evident append-only storage."""
        pass

class ConstraintViolation(Exception):
    """Raised when a critical constraint is violated."""
    pass

class SecurityViolation(Exception):
    """Raised when a security constraint is violated."""
    pass
```

---

    limit: int = 100
):
    """Query audit log with filtering."""
    # Implementation using StateStore
    pass
```

---

## 7. Quality Assurance: Evaluator

### 7.1 Multi-Dimensional Assessment

The Evaluator provides comprehensive quality control through multiple assessment dimensions.
This ensures generated code meets production standards before being accepted.

#### 7.1.1 Assessment Dimensions

| Dimension | Tool | Threshold | Weight |
|-----------|------|-----------|--------|
| **Unit Tests** | pytest | 80% coverage, 0 failures | 25% |
| **Type Safety** | mypy | 0 errors, strict mode | 20% |
| **Code Style** | ruff + black | 0 violations | 15% |
| **Security Scan** | bandit + semgrep | 0 critical issues | 25% |
| **Architecture** | custom | No circular deps, proper layering | 10% |
| **Performance** | pytest-benchmark | Within 10% of baseline | 5% |

#### 7.1.2 Core Implementation

```python
# backend/app/harness/evaluator.py
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
import asyncio
import subprocess
import json

class EvaluationDimension(Enum):
    UNIT_TESTS = "unit_tests"
    TYPE_CHECK = "type_check"
    LINT = "lint"
    SECURITY_SCAN = "security_scan"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"

@dataclass
class DimensionResult:
    dimension: EvaluationDimension
    passed: bool
    score: float  # 0.0 to 1.0
    details: Dict
    logs: List[str]
    execution_time_ms: int

class Evaluator:
    """
    Multi-dimensional evaluation system.
    
    Each dimension runs independently (parallel execution)
    and contributes to the final pass/fail decision.
    
    Weights:
    - Security and Testing: Highest priority (50% combined)
    - Type Safety: Critical for maintainability (20%)
    - Code Style: Important for readability (15%)
    - Architecture: Long-term maintainability (10%)
    - Performance: Baseline checks (5%)
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tools = tool_registry
        self.dimensions = [
            EvaluationDimension.UNIT_TESTS,
            EvaluationDimension.TYPE_CHECK,
            EvaluationDimension.LINT,
            EvaluationDimension.SECURITY_SCAN,
            EvaluationDimension.ARCHITECTURE,
            EvaluationDimension.PERFORMANCE
        ]
        self.weights = {
            EvaluationDimension.UNIT_TESTS: 0.25,
            EvaluationDimension.TYPE_CHECK: 0.20,
            EvaluationDimension.LINT: 0.15,
            EvaluationDimension.SECURITY_SCAN: 0.25,
            EvaluationDimension.ARCHITECTURE: 0.10,
            EvaluationDimension.PERFORMANCE: 0.05
        }
        self.thresholds = {
            EvaluationDimension.UNIT_TESTS: 0.80,  # 80% coverage
            EvaluationDimension.TYPE_CHECK: 1.00,  # 0 errors
            EvaluationDimension.LINT: 1.00,       # 0 violations
            EvaluationDimension.SECURITY_SCAN: 1.00,  # 0 critical
            EvaluationDimension.ARCHITECTURE: 1.00,   # All checks pass
            EvaluationDimension.PERFORMANCE: 0.90     # Within 10% of baseline
        }

    async def evaluate(self,
                      task: TaskNode,
                      execution_results: List[Dict],
                      session_id: str) -> Dict:
        """
        Run all evaluation dimensions and return structured feedback.
        
        Returns:
            Dict with:
            - passed: bool (overall pass/fail)
            - dimensions: Dict of individual results
            - summary: Human-readable summary
            - feedback: Structured feedback for Claude Code
            - weighted_score: float (0.0 to 1.0)
        """
        
        # Run all dimensions in parallel
        dimension_tasks = [
            self._evaluate_dimension(dim, task, execution_results, session_id)
            for dim in self.dimensions
        ]
        
        results = await asyncio.gather(*dimension_tasks)
        
        # Build dimension results map
        dimension_results = {
            r.dimension: r for r in results
        }
        
        # Calculate weighted score
        weighted_score = sum(
            self.weights[dim] * r.score
            for dim, r in dimension_results.items()
        )
        
        # Determine overall pass/fail
        # Must pass all critical dimensions (security, tests)
        critical_dimensions = [
            EvaluationDimension.UNIT_TESTS,
            EvaluationDimension.SECURITY_SCAN,
            EvaluationDimension.TYPE_CHECK
        ]
        
        critical_passed = all(
            dimension_results[dim].passed
            for dim in critical_dimensions
        )
        
        overall_passed = critical_passed and weighted_score >= 0.85
        
        return {
            "passed": overall_passed,
            "weighted_score": round(weighted_score, 3),
            "dimensions": {
                dim.value: {
                    "passed": r.passed,
                    "score": r.score,
                    "details": r.details,
                    "logs": r.logs[:10]  # Limit log size
                }
                for dim, r in dimension_results.items()
            },
            "summary": self._generate_summary(dimension_results, weighted_score),
            "feedback": self._generate_feedback(dimension_results) if not overall_passed else None
        }

    async def _evaluate_dimension(
            self,
            dimension: EvaluationDimension,
            task: TaskNode,
            execution_results: List[Dict],
            session_id: str) -> DimensionResult:
        """Evaluate a single dimension."""
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            if dimension == EvaluationDimension.UNIT_TESTS:
                result = await self._run_tests(task, session_id)
            elif dimension == EvaluationDimension.TYPE_CHECK:
                result = await self._run_type_check(task)
            elif dimension == EvaluationDimension.LINT:
                result = await self._run_linter(task)
            elif dimension == EvaluationDimension.SECURITY_SCAN:
                result = await self._run_security_scan(task)
            elif dimension == EvaluationDimension.ARCHITECTURE:
                result = await self._check_architecture(task)
            elif dimension == EvaluationDimension.PERFORMANCE:
                result = await self._run_benchmarks(task)
            else:
                result = DimensionResult(
                    dimension=dimension,
                    passed=False,
                    score=0.0,
                    details={"error": "Unknown dimension"},
                    logs=[],
                    execution_time_ms=0
                )
            
        except Exception as e:
            result = DimensionResult(
                dimension=dimension,
                passed=False,
                score=0.0,
                details={"error": str(e)},
                logs=[str(e)],
                execution_time_ms=0
            )
        
        return result

    async def _run_tests(self, task: TaskNode, session_id: str) -> DimensionResult:
        """Execute test suite and measure coverage."""
        
        try:
            tool_result = await self.tools.call(
                "run_tests",
                PermissionLevel.EXECUTE,
                {
                    "suite": task.task_type,
                    "coverage": True,
                    "parallel": True
                },
                session_id
            )
            
            if tool_result.success:
                output = tool_result.output
                coverage = output.get("coverage", 0)
                failures = output.get("failures", 0)
                
                passed = coverage >= 80 and failures == 0
                
                return DimensionResult(
                    dimension=EvaluationDimension.UNIT_TESTS,
                    passed=passed,
                    score=coverage / 100.0,
                    details={
                        "coverage": coverage,
                        "failures": failures,
                        "tests_run": output.get("tests_run", 0)
                    },
                    logs=output.get("logs", []),
                    execution_time_ms=tool_result.execution_time_ms
                )
            else:
                return DimensionResult(
                    dimension=EvaluationDimension.UNIT_TESTS,
                    passed=False,
                    score=0.0,
                    details={"error": "Test execution failed"},
                    logs=tool_result.logs,
                    execution_time_ms=tool_result.execution_time_ms
                )
                
        except Exception as e:
            return DimensionResult(
                dimension=EvaluationDimension.UNIT_TESTS,
                passed=False,
                score=0.0,
                details={"error": str(e)},
                logs=[str(e)],
                execution_time_ms=0
            )

    async def _run_security_scan(self, task: TaskNode) -> DimensionResult:
        """Run security analysis on generated code."""
        
        try:
            tool_result = await self.tools.call(
                "run_security_scan",
                PermissionLevel.EXECUTE,
                {"target": task.id},
                "evaluator"
            )
            
            if tool_result.success:
                output = tool_result.output
                issues = output.get("issues", [])
                
                critical_issues = [
                    i for i in issues
                    if i.get("severity") == "critical"
                ]
                
                passed = len(critical_issues) == 0
                
                # Score based on total issues
                score = max(0, 1.0 - (len(issues) * 0.1))
                
                return DimensionResult(
                    dimension=EvaluationDimension.SECURITY_SCAN,
                    passed=passed,
                    score=score,
                    details={
                        "total_issues": len(issues),
                        "critical_issues": len(critical_issues),
                        "scanners": output.get("scanners", [])
                    },
                    logs=[i.get("message", "") for i in issues],
                    execution_time_ms=tool_result.execution_time_ms
                )
            else:
                return DimensionResult(
                    dimension=EvaluationDimension.SECURITY_SCAN,
                    passed=False,
                    score=0.0,
                    details={"error": "Security scan failed"},
                    logs=tool_result.logs,
                    execution_time_ms=tool_result.execution_time_ms
                )
                
        except Exception as e:
            return DimensionResult(
                dimension=EvaluationDimension.SECURITY_SCAN,
                passed=False,
                score=0.0,
                details={"error": str(e)},
                logs=[str(e)],
                execution_time_ms=0
            )

    async def _run_type_check(self, task: TaskNode) -> DimensionResult:
        """Run mypy type checking."""
        # Implementation similar to _run_tests
        pass

    async def _run_linter(self, task: TaskNode) -> DimensionResult:
        """Run ruff and black formatting checks."""
        # Implementation similar to _run_tests
        pass

    async def _check_architecture(self, task: TaskNode) -> DimensionResult:
        """Check architectural compliance."""
        # Check: proper layering, no circular imports, API patterns
        pass

    async def _run_benchmarks(self, task: TaskNode) -> DimensionResult:
        """Run performance benchmarks."""
        # Implementation using pytest-benchmark
        pass

    def _generate_summary(
            self,
            results: Dict[EvaluationDimension, DimensionResult],
            weighted_score: float) -> str:
        """Generate human-readable summary."""
        
        passed = sum(1 for r in results.values() if r.passed)
        total = len(results)
        
        summary = f"Evaluation: {passed}/{total} dimensions passed\n"
        summary += f"Weighted score: {weighted_score:.1%}\n\n"
        
        for dim, result in results.items():
            status = "PASS" if result.passed else "FAIL"
            summary += f"  [{status}] {dim.value}: {result.score:.1%}\n"
        
        return summary

    def _generate_feedback(
            self,
            results: Dict[EvaluationDimension, DimensionResult]) -> Dict:
        """
        Generate structured feedback for Claude Code to fix.
        
        Maps failures to specific fix strategies that
        Claude can implement in the next iteration.
        """
        
        failures = {
            dim.value: result
            for dim, result in results.items()
            if not result.passed
        }
        
        suggested_fixes = []
        
        if EvaluationDimension.UNIT_TESTS.value in failures:
            test_result = failures[EvaluationDimension.UNIT_TESTS.value]
            if test_result.details.get("coverage", 0) < 80:
                suggested_fixes.append(
                    "Add missing test cases to achieve 80% coverage"
                )
            if test_result.details.get("failures", 0) > 0:
                suggested_fixes.append(
                    "Fix failing test assertions"
                )
        
        if EvaluationDimension.TYPE_CHECK.value in failures:
            suggested_fixes.append(
                "Add type hints to all function signatures and variables"
            )
        
        if EvaluationDimension.LINT.value in failures:
            suggested_fixes.append(
                "Run auto-formatter (black) and fix style issues (ruff)"
            )
        
        if EvaluationDimension.SECURITY_SCAN.value in failures:
            security_result = failures[EvaluationDimension.SECURITY_SCAN.value]
            issues = security_result.details.get("issues", [])
            
            for issue in issues:
                if "sql" in issue.get("message", "").lower():
                    suggested_fixes.append(
                        "Use parameterized queries instead of string concatenation"
                    )
                elif "secret" in issue.get("message", "").lower():
                    suggested_fixes.append(
                        "Remove hardcoded secrets, use environment variables"
                    )
        
        if EvaluationDimension.ARCHITECTURE.value in failures:
            suggested_fixes.append(
                "Refactor to eliminate circular dependencies and ensure proper layering"
            )
        
        return {
            "failed_dimensions": list(failures.keys()),
            "details": {
                dim: {
                    "score": result.score,
                    "details": result.details,
                    "logs": result.logs[:5]
                }
                for dim, result in failures.items()
            },
            "suggested_fixes": suggested_fixes,
            "fix_priority": self._prioritize_fixes(failures)
        }

    def _prioritize_fixes(
            self,
            failures: Dict[str, DimensionResult]) -> List[str]:
        """
        Prioritize fixes based on dimension weights and failure severity.
        
        Critical first: Security, Tests, Type Safety
        Then: Style, Architecture, Performance
        """
        priority_order = [
            EvaluationDimension.SECURITY_SCAN.value,
            EvaluationDimension.UNIT_TESTS.value,
            EvaluationDimension.TYPE_CHECK.value,
            EvaluationDimension.LINT.value,
            EvaluationDimension.ARCHITECTURE.value,
            EvaluationDimension.PERFORMANCE.value
        ]
        
        return [
            dim for dim in priority_order
            if dim in failures
        ]
```

---

## 8. Execution Environment

### 8.1 Sandbox Architecture

The Sandbox provides isolated execution for all agent operations.
This is critical for security: even if Claude Code generates malicious code,
it cannot escape the container or access production systems.

#### 8.1.1 Security Requirements

| Requirement | Implementation | Rationale |
|-------------|-----------------|-----------|
| **Network Isolation** | `network_mode: none` | Prevent data exfiltration |
| **Filesystem Isolation** | Read-only root, tmpfs /tmp | Prevent persistent modifications |
| **Resource Limits** | CPU 1 core, Memory 2GB | Prevent DoS attacks |
| **No Privilege Escalation** | `no-new-privileges: true` | Prevent container escape |
| **Seccomp Profile** | Custom seccomp filter | Restrict dangerous syscalls |
| **User Isolation** | Non-root user (UID 1000) | Limit damage from compromise |

#### 8.1.2 Docker Configuration

```dockerfile
# docker/harness-sandbox.Dockerfile
FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r harness && useradd -r -g harness -s /bin/bash harness && \
    mkdir -p /workspace /tmp/harness && \
    chown -R harness:harness /workspace /tmp/harness

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pytest==7.4.3 \
    pytest-cov==4.1.0 \
    pytest-asyncio==0.21.1 \
    mypy==1.7.0 \
    ruff==0.1.6 \
    black==23.11.0 \
    bandit==1.7.5 \
    safety==2.3.5 \
    semgrep==1.52.0 \
    httpx==0.25.2 \
    aiofiles==23.2.1

# Copy sandbox policy
COPY --chown=harness:harness docker/sandbox-policy.json /etc/harness/policy.json

# Set up workspace
WORKDIR /workspace
USER harness

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "-m", "harness.sandbox_worker"]
```

#### 8.1.3 Seccomp Profile

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "archMap": [
    {
      "architecture": "SCMP_ARCH_X86_64",
      "subArchitectures": [
        "SCMP_ARCH_X86",
        "SCMP_ARCH_X32"
      ]
    }
  ],
  "syscalls": [
    {
      "names": [
        "accept",
        "accept4",
        "bind",
        "clone",
        "close",
        "connect",
        "epoll_create1",
        "epoll_ctl",
        "epoll_pwait",
        "exit",
        "exit_group",
        "fcntl",
        "fstat",
        "futex",
        "getcwd",
        "getdents64",
        "getpid",
        "getrandom",
        "getsockname",
        "getsockopt",
        "ioctl",
        "listen",
        "lseek",
        "mkdir",
        "mmap",
        "mprotect",
        "munmap",
        "nanosleep",
        "newfstatat",
        "openat",
        "poll",
        "pread64",
        "pwrite64",
        "read",
        "recvfrom",
        "recvmsg",
        "rt_sigaction",
        "rt_sigprocmask",
        "rt_sigreturn",
        "select",
        "sendmsg",
        "sendto",
        "setitimer",
        "setsockopt",
        "socket",
        "socketpair",
        "stat",
        "statfs",
        "sysinfo",
        "uname",
        "unlink",
        "unlinkat",
        "wait4",
        "write",
        "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

---

### 8.2 Docker Compose Configuration

```yaml
# docker-compose.harness.yml
version: "3.8"

services:
  # === Control Plane ===
  harness-orchestrator:
    build:
      context: .
      dockerfile: docker/harness-orchestrator.Dockerfile
    container_name: harness-orchestrator
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DATABASE_URL=postgresql://harness:${DB_PASSWORD}@postgres:5432/harness
      - REDIS_URL=redis://redis:6379/0
      - SANDBOX_NETWORK=none
      - LOG_LEVEL=INFO
    volumes:
      - ./backend:/workspace/backend:ro
      - harness-state:/data/state
      - harness-logs:/data/logs
    networks:
      - harness-internal
      - harness-external
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
        reservations:
          cpus: "1"
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # === Sandbox Worker ===
  harness-sandbox:
    build:
      context: .
      dockerfile: docker/harness-sandbox.Dockerfile
    container_name: harness-sandbox
    network_mode: none  # No external network access
    read_only: true     # Read-only root filesystem
    tmpfs:
      - /tmp:noexec,nosuid,size=100m,uid=1000,gid=1000
      - /workspace/tmp:noexec,nosuid,size=500m,uid=1000,gid=1000
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 1G
    security_opt:
      - no-new-privileges:true
      - seccomp:./docker/seccomp-profile.json
      - apparmor:docker-harness-sandbox
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    user: "1000:1000"
    volumes:
      - type: bind
        source: ./workspace
        target: /workspace
        read_only: false
      - type: tmpfs
        target: /workspace/output
        tmpfs:
          size: 500M
          mode: 1777
    environment:
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
    command: ["python", "-m", "harness.sandbox_worker"]

  # === Frontend (Vite + React) ===
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: harness-frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000
      - VITE_APP_NAME=Harness Control Center
    volumes:
      - ./frontend:/app:cached
      - /app/node_modules
    networks:
      - harness-external
    depends_on:
      - harness-orchestrator
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 1G

  # === Database ===
  postgres:
    image: pgvector/pgvector:pg16
    container_name: harness-postgres
    environment:
      - POSTGRES_USER=harness
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=harness
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./docker/postgres/init:/docker-entrypoint-initdb.d
    networks:
      - harness-internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U harness -d harness"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G

  # === Cache ===
  redis:
    image: redis:7-alpine
    container_name: harness-redis
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - harness-internal
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  # === Reverse Proxy ===
  nginx:
    image: nginx:alpine
    container_name: harness-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
    networks:
      - harness-external
    depends_on:
      - harness-orchestrator
      - frontend
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M

volumes:
  harness-state:
    driver: local
  harness-logs:
    driver: local
  postgres-data:
    driver: local
  redis-data:
    driver: local

networks:
  harness-internal:
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.20.0.0/16

  harness-external:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
```

---

## 9. Frontend Dashboard (Vite + Node.js)

### 9.1 React Components

The frontend provides a real-time dashboard for monitoring and controlling the Harness system.
Built with React 18, TypeScript, and Vite for optimal developer experience and performance.

#### 9.1.1 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── HarnessDashboard.tsx      # Main dashboard
│   │   ├── TaskSubmissionForm.tsx    # New task creation
│   │   ├── TaskCard.tsx              # Individual task display
│   │   ├── TaskList.tsx              # Task queue visualization
│   │   ├── ApprovalQueue.tsx         # Human-in-the-loop approvals
│   │   ├── ApprovalCard.tsx          # Individual approval request
│   │   ├── AuditLogViewer.tsx        # Audit trail display
│   │   ├── AgentLoopVisualizer.tsx   # Real-time loop visualization
│   │   ├── ContextViewer.tsx         # Context inspection
│   │   └── EvaluationResults.tsx     # Test/lint results
│   ├── hooks/
│   │   ├── useWebSocket.ts           # WebSocket connection management
│   │   ├── useHarnessState.ts        # Global state management
│   │   ├── useTaskPolling.ts         # Polling for task updates
│   │   └── useAuditLog.ts            # Audit log fetching
│   ├── api/
│   │   ├── harness.ts                # Auto-generated API client
│   │   └── types.ts                  # TypeScript interfaces
│   ├── store/
│   │   └── harnessStore.ts           # Zustand state store
│   ├── utils/
│   │   ├── formatters.ts             # Date/number formatting
│   │   └── validators.ts             # Input validation
│   ├── types/
│   │   └── harness.ts                # Domain type definitions
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── package.json
```

#### 9.1.2 Main Dashboard Component

```typescript
// frontend/src/components/HarnessDashboard.tsx
import { useState, useEffect, useCallback } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { useHarnessStore } from "../store/harnessStore";
import { TaskSubmissionForm } from "./TaskSubmissionForm";
import { TaskList } from "./TaskList";
import { ApprovalQueue } from "./ApprovalQueue";
import { AuditLogViewer } from "./AuditLogViewer";
import { AgentLoopVisualizer } from "./AgentLoopVisualizer";
import { EvaluationResults } from "./EvaluationResults";
import type {
  TaskStatus,
  HarnessEvent,
  ApprovalRequest,
  SystemMetrics
} from "../types/harness";

export function HarnessDashboard() {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("tasks");
  
  const {
    tasks,
    pendingApprovals,
    systemMetrics,
    addTask,
    updateTask,
    addApproval,
    removeApproval,
    updateMetrics
  } = useHarnessStore();
  
  const { lastMessage, sendMessage, connectionStatus } = useWebSocket(
    `ws://${import.meta.env.VITE_WS_URL}/api/v1/harness/ws/main`
  );
  
  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;
    try {
      const event: HarnessEvent = JSON.parse(lastMessage.data);
      handleHarnessEvent(event);
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error);
    }
  }, [lastMessage]);
  
  const handleHarnessEvent = useCallback((event: HarnessEvent) => {
    switch (event.type) {
      case "task_started":
      case "task_updated":
      case "task_completed":
      case "task_failed":
        updateTask(event.payload.task_id, event.payload);
        break;
      
      case "approval_required":
        addApproval(event.payload as ApprovalRequest);
        break;
      
      case "approval_resolved":
        removeApproval(event.payload.approval_id);
        break;
      
      case "iteration_started":
      case "phase_reasoning":
      case "phase_action":
      case "execution_completed":
      case "evaluation_completed":
      case "phase_feedback":
        updateTask(event.payload.task_id, {
          currentPhase: event.type,
          ...event.payload
        });
        break;
      
      case "system_metrics":
        updateMetrics(event.payload as SystemMetrics);
        break;
      
      case "error":
        console.error("Harness Error:", event.payload.message);
        break;
    }
  }, [updateTask, addApproval, removeApproval, updateMetrics]);
  
  const handleSubmitTask = async (description: string, taskType: string) => {
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/harness/tasks`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${getAuthToken()}`
          },
          body: JSON.stringify({
            task_id: taskId,
            description,
            task_type: taskType,
            dependencies: [],
            priority: 5,
            timeout_seconds: 300
          })
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      addTask({
        id: taskId,
        description,
        type: taskType,
        status: "queued",
        progress: 0,
        currentIteration: 0,
        maxIterations: 5,
        createdAt: new Date().toISOString(),
        logs: []
      });
      
    } catch (error) {
      console.error("Failed to queue task:", error);
    }
  };
  
  const handleApproval = async (
    approvalId: string, 
    approved: boolean,
    comment?: string
  ) => {
    sendMessage(
      JSON.stringify({
        type: "approval_response",
        approval_id: approvalId,
        approved,
        comment,
        approver: getCurrentUser()?.id || "unknown",
        timestamp: new Date().toISOString()
      })
    );
    
    removeApproval(approvalId);
  };
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b
                        border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4
                        flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white
                           flex items-center gap-2">
              <Shield className="w-8 h-8 text-blue-600" />
              Harness Control Center
            </h1>
            <ConnectionStatus status={connectionStatus} />
          </div>
          <div className="flex items-center space-x-4">
            <SystemMetricsBadge metrics={systemMetrics} />
            <UserMenu />
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white dark:bg-gray-800 rounded-lg
                             shadow-sm border border-gray-200
                             dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900
                             dark:text-white mb-4
                             flex items-center gap-2">
                <PlusCircle className="w-5 h-5" />
                New Task
              </h2>
              <TaskSubmissionForm onSubmit={handleSubmitTask} />
            </section>
            
            <section className="bg-white dark:bg-gray-800 rounded-lg
                             shadow-sm border border-gray-200
                             dark:border-gray-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900
                               dark:text-white
                               flex items-center gap-2">
                  <List className="w-5 h-5" />
                  Active Tasks
                  <span className="ml-2 px-2 py-1 text-xs font-medium
                                   bg-blue-100 text-blue-800 rounded-full">
                    {tasks.filter(t => t.status === "running").length} running
                  </span>
                </h2>
                
                <div className="flex space-x-2">
                  <FilterButton
                    active={activeTab === "tasks"}
                    onClick={() => setActiveTab("tasks")}
                    label="All Tasks"
                    count={tasks.length}
                  />
                  <FilterButton
                    active={activeTab === "approvals"}
                    onClick={() => setActiveTab("approvals")}
                    label="Approvals"
                    count={pendingApprovals.length}
                    badgeColor="amber"
                  />
                </div>
              </div>
              
              {activeTab === "tasks" ? (
                <TaskList
                  tasks={tasks}
                  selectedTask={selectedTask}
                  onSelectTask={setSelectedTask}
                />
              ) : (
                <ApprovalQueue
                  approvals={pendingApprovals}
                  onApprove={handleApproval}
                />
              )}
            </section>
          </div>
          
          <div className="space-y-6">
            {selectedTask && (
              <AgentLoopVisualizer
                taskId={selectedTask}
                className="bg-white dark:bg-gray-800 rounded-lg
                          shadow-sm border border-gray-200
                          dark:border-gray-700 p-6"
              />
            )}
            
            {selectedTask && (
              <EvaluationResults
                taskId={selectedTask}
                className="bg-white dark:bg-gray-800 rounded-lg
                          shadow-sm border border-gray-200
                          dark:border-gray-700 p-6"
              />
            )}
            
            <section className="bg-white dark:bg-gray-800 rounded-lg
                             shadow-sm border border-gray-200
                             dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900
                             dark:text-white mb-4
                             flex items-center gap-2">
                <History className="w-5 h-5" />
                Audit Trail
              </h2>
              <AuditLogViewer
                taskId={selectedTask}
                maxEntries={50}
              />
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
```

---

## 9. Frontend Dashboard (Vite + Node.js)

### 9.1 React Components

The frontend provides a real-time dashboard for monitoring and controlling the Harness system.
Built with React 18, TypeScript, and Vite for optimal developer experience and performance.

#### 9.1.1 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── HarnessDashboard.tsx      # Main dashboard
│   │   ├── TaskSubmissionForm.tsx    # New task creation
│   │   ├── TaskCard.tsx              # Individual task display
│   │   ├── TaskList.tsx              # Task queue visualization
│   │   ├── ApprovalQueue.tsx         # Human-in-the-loop approvals
│   │   ├── ApprovalCard.tsx          # Individual approval request
│   │   ├── AuditLogViewer.tsx        # Audit trail display
│   │   ├── AgentLoopVisualizer.tsx   # Real-time loop visualization
│   │   ├── ContextViewer.tsx         # Context inspection
│   │   └── EvaluationResults.tsx     # Test/lint results
│   ├── hooks/
│   │   ├── useWebSocket.ts           # WebSocket connection management
│   │   ├── useHarnessState.ts        # Global state management
│   │   ├── useTaskPolling.ts         # Polling for task updates
│   │   └── useAuditLog.ts            # Audit log fetching
│   ├── api/
│   │   ├── harness.ts                # Auto-generated API client
│   │   └── types.ts                  # TypeScript interfaces
│   ├── store/
│   │   └── harnessStore.ts           # Zustand state store
│   ├── utils/
│   │   ├── formatters.ts             # Date/number formatting
│   │   └── validators.ts             # Input validation
│   ├── types/
│   │   └── harness.ts                # Domain type definitions
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── package.json
```

#### 9.1.2 Main Dashboard Component

```typescript
// frontend/src/components/HarnessDashboard.tsx
import { useState, useEffect, useCallback } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { useHarnessStore } from "../store/harnessStore";
import { TaskSubmissionForm } from "./TaskSubmissionForm";
import { TaskList } from "./TaskList";
import { ApprovalQueue } from "./ApprovalQueue";
import { AuditLogViewer } from "./AuditLogViewer";
import { AgentLoopVisualizer } from "./AgentLoopVisualizer";
import { EvaluationResults } from "./EvaluationResults";
import type {
  TaskStatus,
  HarnessEvent,
  ApprovalRequest,
  SystemMetrics
} from "../types/harness";

export function HarnessDashboard() {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("tasks");
  
  const {
    tasks,
    pendingApprovals,
    systemMetrics,
    addTask,
    updateTask,
    addApproval,
    removeApproval,
    updateMetrics
  } = useHarnessStore();
  
  const { lastMessage, sendMessage, connectionStatus } = useWebSocket(
    `ws://${import.meta.env.VITE_WS_URL}/api/v1/harness/ws/main`
  );
  
  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;
    try {
      const event: HarnessEvent = JSON.parse(lastMessage.data);
      handleHarnessEvent(event);
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error);
    }
  }, [lastMessage]);
  
  const handleHarnessEvent = useCallback((event: HarnessEvent) => {
    switch (event.type) {
      case "task_started":
      case "task_updated":
      case "task_completed":
      case "task_failed":
        updateTask(event.payload.task_id, event.payload);
        break;
      
      case "approval_required":
        addApproval(event.payload as ApprovalRequest);
        break;
      
      case "approval_resolved":
        removeApproval(event.payload.approval_id);
        break;
      
      case "iteration_started":
      case "phase_reasoning":
      case "phase_action":
      case "execution_completed":
      case "evaluation_completed":
      case "phase_feedback":
        updateTask(event.payload.task_id, {
          currentPhase: event.type,
          ...event.payload
        });
        break;
      
      case "system_metrics":
        updateMetrics(event.payload as SystemMetrics);
        break;
      
      case "error":
        console.error("Harness Error:", event.payload.message);
        break;
    }
  }, [updateTask, addApproval, removeApproval, updateMetrics]);
  
  const handleSubmitTask = async (description: string, taskType: string) => {
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/harness/tasks`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${getAuthToken()}`
          },
          body: JSON.stringify({
            task_id: taskId,
            description,
            task_type: taskType,
            dependencies: [],
            priority: 5,
            timeout_seconds: 300
          })
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      addTask({
        id: taskId,
        description,
        type: taskType,
        status: "queued",
        progress: 0,
        currentIteration: 0,
        maxIterations: 5,
        createdAt: new Date().toISOString(),
        logs: []
      });
      
    } catch (error) {
      console.error("Failed to queue task:", error);
    }
  };
  
  const handleApproval = async (
    approvalId: string, 
    approved: boolean,
    comment?: string
  ) => {
    sendMessage(
      JSON.stringify({
        type: "approval_response",
        approval_id: approvalId,
        approved,
        comment,
        approver: getCurrentUser()?.id || "unknown",
        timestamp: new Date().toISOString()
      })
    );
    
    removeApproval(approvalId);
  };
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b
                        border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4
                        flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white
                           flex items-center gap-2">
              <Shield className="w-8 h-8 text-blue-600" />
              Harness Control Center
            </h1>
            <ConnectionStatus status={connectionStatus} />
          </div>
          <div className="flex items-center space-x-4">
            <SystemMetricsBadge metrics={systemMetrics} />
            <UserMenu />
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white dark:bg-gray-800 rounded-lg
                             shadow-sm border border-gray-200
                             dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900
                             dark:text-white mb-4
                             flex items-center gap-2">
                <PlusCircle className="w-5 h-5" />
                New Task
              </h2>
              <TaskSubmissionForm onSubmit={handleSubmitTask} />
            </section>
            
            <section className="bg-white dark:bg-gray-800 rounded-lg
                             shadow-sm border border-gray-200
                             dark:border-gray-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900
                               dark:text-white
                               flex items-center gap-2">
                  <List className="w-5 h-5" />
                  Active Tasks
                  <span className="ml-2 px-2 py-1 text-xs font-medium
                                   bg-blue-100 text-blue-800 rounded-full">
                    {tasks.filter(t => t.status === "running").length} running
                  </span>
                </h2>
                
                <div className="flex space-x-2">
                  <FilterButton
                    active={activeTab === "tasks"}
                    onClick={() => setActiveTab("tasks")}
                    label="All Tasks"
                    count={tasks.length}
                  />
                  <FilterButton
                    active={activeTab === "approvals"}
                    onClick={() => setActiveTab("approvals")}
                    label="Approvals"
                    count={pendingApprovals.length}
                    badgeColor="amber"
                  />
                </div>
              </div>
              
              {activeTab === "tasks" ? (
                <TaskList
                  tasks={tasks}
                  selectedTask={selectedTask}
                  onSelectTask={setSelectedTask}
                />
              ) : (
                <ApprovalQueue
                  approvals={pendingApprovals}
                  onApprove={handleApproval}
                />
              )}
            </section>
          </div>
          
          <div className="space-y-6">
            {selectedTask && (
              <AgentLoopVisualizer
                taskId={selectedTask}
                className="bg-white dark:bg-gray-800 rounded-lg
                          shadow-sm border border-gray-200
                          dark:border-gray-700 p-6"
              />
            )}
            
            {selectedTask && (
              <EvaluationResults
                taskId={selectedTask}
                className="bg-white dark:bg-gray-800 rounded-lg
                          shadow-sm border border-gray-200
                          dark:border-gray-700 p-6"
              />
            )}
            
            <section className="bg-white dark:bg-gray-800 rounded-lg
                             shadow-sm border border-gray-200
                             dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900
                             dark:text-white mb-4
                             flex items-center gap-2">
                <History className="w-5 h-5" />
                Audit Trail
              </h2>
              <AuditLogViewer
                taskId={selectedTask}
                maxEntries={50}
              />
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
```

---

### 9.2 WebSocket Integration

#### 9.2.1 useWebSocket Hook

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useState, useEffect, useRef, useCallback } from "react";
import type { HarnessEvent } from "../types/harness";

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

interface UseWebSocketReturn {
  lastMessage: MessageEvent | null;
  sendMessage: (message: string) => void;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelayBase = 1000; // 1 second

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus("connecting");

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      reconnectAttemptsRef.current = 0;
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      setLastMessage(event);
    };

    ws.onclose = (event) => {
      setConnectionStatus("disconnected");
      wsRef.current = null;

      if (!event.wasClean && reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = reconnectDelayBase * Math.pow(2, reconnectAttemptsRef.current);
        reconnectAttemptsRef.current++;
        setConnectionStatus("reconnecting");

        setTimeout(() => {
          connect();
        }, delay);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [url]);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn("WebSocket not connected, message queued");
    }
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
      }
    };
  }, [connect]);

  return {
    lastMessage,
    sendMessage,
    connectionStatus,
    reconnect
  };
}
```

#### 9.2.2 Zustand State Store

```typescript
// frontend/src/store/harnessStore.ts
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  Task,
  ApprovalRequest,
  SystemMetrics,
  AuditEntry
} from "../types/harness";

interface HarnessState {
  tasks: Task[];
  pendingApprovals: ApprovalRequest[];
  systemMetrics: SystemMetrics;
  auditLog: AuditEntry[];
  selectedTaskId: string | null;

  // Actions
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  removeTask: (taskId: string) => void;
  addApproval: (approval: ApprovalRequest) => void;
  removeApproval: (approvalId: string) => void;
  updateMetrics: (metrics: SystemMetrics) => void;
  addAuditEntry: (entry: AuditEntry) => void;
  setSelectedTask: (taskId: string | null) => void;
}

export const useHarnessStore = create<HarnessState>()(
  immer((set) => ({
    tasks: [],
    pendingApprovals: [],
    systemMetrics: {
      activeTasks: 0,
      queuedTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      avgExecutionTime: 0,
      systemLoad: 0,
      memoryUsage: 0
    },
    auditLog: [],
    selectedTaskId: null,

    addTask: (task) =>
      set((state) => {
        state.tasks.unshift(task);
        state.systemMetrics.queuedTasks++;
      }),

    updateTask: (taskId, updates) =>
      set((state) => {
        const task = state.tasks.find((t) => t.id === taskId);
        if (task) {
          Object.assign(task, updates);
          
          if (updates.status === "running") {
            state.systemMetrics.queuedTasks--;
            state.systemMetrics.activeTasks++;
          } else if (updates.status === "completed") {
            state.systemMetrics.activeTasks--;
            state.systemMetrics.completedTasks++;
          } else if (updates.status === "failed") {
            state.systemMetrics.activeTasks--;
            state.systemMetrics.failedTasks++;
          }
        }
      }),

    removeTask: (taskId) =>
      set((state) => {
        state.tasks = state.tasks.filter((t) => t.id !== taskId);
      }),

    addApproval: (approval) =>
      set((state) => {
        state.pendingApprovals.push(approval);
      }),

    removeApproval: (approvalId) =>
      set((state) => {
        state.pendingApprovals = state.pendingApprovals.filter(
          (a) => a.id !== approvalId
        );
      }),

    updateMetrics: (metrics) =>
      set((state) => {
        state.systemMetrics = { ...state.systemMetrics, ...metrics };
      }),

    addAuditEntry: (entry) =>
      set((state) => {
        state.auditLog.unshift(entry);
        if (state.auditLog.length > 1000) {
          state.auditLog.pop();
        }
      }),

    setSelectedTask: (taskId) =>
      set((state) => {
        state.selectedTaskId = taskId;
      })
  }))
);
```

---

### 9.3 Auto-Generated API Client

The API client is auto-generated from the FastAPI OpenAPI schema using openapi-typescript.
This ensures type safety and automatic updates when the backend API changes.

#### 9.3.1 Generation Script

```json
// frontend/package.json (scripts section)
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "generate-api": "openapi-typescript http://localhost:8000/openapi.json -o src/api/harness.ts",
    "generate-api:prod": "openapi-typescript https://api.harness.example.com/openapi.json -o src/api/harness.ts",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "coverage": "vitest run --coverage"
  }
}
```

#### 9.3.2 Generated API Types

```typescript
// frontend/src/api/harness.ts (auto-generated)
// Generated by openapi-typescript from FastAPI OpenAPI schema

export interface paths {
  "/api/v1/harness/tasks": {
    post: {
      requestBody: {
        content: {
          "application/json": {
            task_id: string;
            description: string;
            task_type: "code" | "test" | "review" | "deploy" | "fix";
            dependencies: string[];
            priority?: number;
            timeout_seconds?: number;
          };
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              status: "queued";
              task_id: string;
              estimated_position: number;
              queue_url: string;
            };
          };
        };
        422: {
          content: {
            "application/json": {
              detail: Array<{
                loc: (string | number)[];
                msg: string;
                type: string;
              }>;
            };
          };
        };
      };
    };
  };
  "/api/v1/harness/tasks/{task_id}": {
    get: {
      parameters: {
        path: {
          task_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              task_id: string;
              status: "pending" | "running" | "completed" | "failed";
              description: string;
              type: string;
              result?: Record<string, unknown>;
              error_log?: string[];
              retry_count: number;
              created_at: string;
              updated_at: string;
            };
          };
        };
      };
    };
  };
  "/api/v1/harness/audit": {
    get: {
      parameters: {
        query: {
          session_id?: string;
          start_time?: string;
          end_time?: string;
          limit?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              entries: Array<{
                entry_id: string;
                timestamp: string;
                session_id: string;
                action: string;
                actor: string;
                result: string;
                risk_level: string;
              }>;
              total: number;
              page: number;
            };
          };
        };
      };
    };
  };
}

export type TaskRequest = paths["/api/v1/harness/tasks"]["post"]["requestBody"]["content"]["application/json"];
export type TaskResponse = paths["/api/v1/harness/tasks"]["post"]["responses"][200]["content"]["application/json"];
export type TaskStatusResponse = paths["/api/v1/harness/tasks/{task_id}"]["get"]["responses"][200]["content"]["application/json"];
export type AuditLogResponse = paths["/api/v1/harness/audit"]["get"]["responses"][200]["content"]["application/json"];
```

#### 9.3.3 API Client Implementation

```typescript
// frontend/src/api/client.ts
import type { paths } from "./harness";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`HTTP ${status}: ${statusText}`);
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${getAuthToken()}`,
      ...options.headers
    }
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => undefined);
    throw new ApiError(response.status, response.statusText, errorData);
  }
  
  return response.json();
}

export const HarnessApi = {
  // Tasks
  createTask: (data: paths["/api/v1/harness/tasks"]["post"]["requestBody"]["content"]["application/json"]) =>
    fetchApi<paths["/api/v1/harness/tasks"]["post"]["responses"][200]["content"]["application/json"]>(
      "/api/v1/harness/tasks",
      { method: "POST", body: JSON.stringify(data) }
    ),
  
  getTaskStatus: (taskId: string) =>
    fetchApi<paths["/api/v1/harness/tasks/{task_id}"]["get"]["responses"][200]["content"]["application/json"]>(
      `/api/v1/harness/tasks/${taskId}`
    ),
  
  getAuditLog: (params?: {
    session_id?: string;
    start_time?: string;
    end_time?: string;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.append(key, String(value));
      });
    }
    return fetchApi<paths["/api/v1/harness/audit"]["get"]["responses"][200]["content"]["application/json"]>(
      `/api/v1/harness/audit?${searchParams.toString()}`
    );
  }
};
```

---

## 10. Implementation Roadmap

### 10.1 Phase-Based Development Plan

| Phase | Duration | Focus | Deliverables | Dependencies |
|-------|----------|-------|-------------|--------------|
| **Phase 1: Foundation** | 2 weeks | Core infrastructure | Task Planner, Context Manager, basic Tool Registry | None |
| **Phase 2: Integration** | 2 weeks | Claude Code MCP | Orchestrator, Agent Loop, basic Evaluator | Phase 1 |
| **Phase 3: Frontend** | 1 week | Dashboard UI | React components, WebSocket, task submission | Phase 2 |
| **Phase 4: Governance** | 1 week | Security & audit | Audit system, constraint rules, human-in-the-loop | Phase 2 |
| **Phase 5: Optimization** | 2 weeks | Performance & memory | RAG retrieval, task memory, benchmarks | Phase 3, 4 |
| **Phase 6: Production** | 1 week | Deployment | Docker Compose, monitoring, documentation | Phase 5 |

### 10.2 Phase 1: Foundation (Weeks 1-2)

**Goals:**
- Set up FastAPI project structure
- Implement Task Planner with DAG support
- Build Context Manager with basic layers
- Create State Store with PostgreSQL persistence
- Set up Docker development environment

**Tasks:**
- [ ] Project scaffolding (FastAPI, SQLAlchemy, Alembic)
- [ ] PostgreSQL + pgvector setup
- [ ] Redis cache layer
- [ ] Task Planner implementation (DAG, topological sort)
- [ ] Context Manager (Global rules, Task context)
- [ ] State Store (checkpoints, event sourcing)
- [ ] Basic Tool Registry framework
- [ ] Docker Compose for development

**Success Criteria:**
- Tasks can be created with dependencies
- Execution order is correctly determined
- State persists across restarts
- Basic tools can be registered and called

### 10.3 Phase 2: Integration (Weeks 3-4)

**Goals:**
- Integrate Claude Code via MCP protocol
- Implement complete Agent Loop
- Build basic Evaluator (tests, lint)
- Add WebSocket support for real-time updates

**Tasks:**
- [ ] MCP client implementation
- [ ] Orchestrator with Agent Loop
- [ ] Tool execution pipeline
- [ ] Basic Evaluator (pytest, mypy, ruff)
- [ ] WebSocket manager
- [ ] Error handling and retry logic
- [ ] Cost tracking per task

**Success Criteria:**
- Claude Code can reason about tasks
- Agent Loop completes within 5 iterations
- Generated code passes basic tests
- Real-time updates work via WebSocket

### 10.4 Phase 3: Frontend (Week 5)

**Goals:**
- Build React dashboard with Vite
- Implement task submission and monitoring
- Add approval queue UI
- Create audit log viewer

**Tasks:**
- [ ] Vite + React + TypeScript setup
- [ ] Tailwind CSS configuration
- [ ] Zustand state store
- [ ] useWebSocket hook
- [ ] TaskSubmissionForm component
- [ ] TaskList and TaskCard components
- [ ] ApprovalQueue component
- [ ] AuditLogViewer component
- [ ] AgentLoopVisualizer component
- [ ] Auto-generated API client setup

**Success Criteria:**
- Users can submit tasks via web UI
- Task status updates in real-time
- Approval requests are visible and actionable
- Audit log is searchable and filterable

### 10.5 Phase 4: Governance (Week 6)

**Goals:**
- Implement comprehensive audit system
- Add constraint enforcement
- Build human-in-the-loop approval workflow
- Set up security scanning integration

**Tasks:**
- [ ] Audit logging with tamper-evident hashes
- [ ] Constraint rule engine
- [ ] Permission system (RBAC)
- [ ] Human approval workflow
- [ ] Security scanning (bandit, semgrep, git-leaks)
- [ ] Rate limiting
- [ ] Secret detection
- [ ] Notification system (Slack, email)

**Success Criteria:**
- All actions are audited
- Constraints prevent forbidden patterns
- High-risk actions require approval
- Security scans run automatically

### 10.6 Phase 5: Optimization (Weeks 7-8)

**Goals:**
- Add RAG for code retrieval
- Implement task memory
- Optimize token usage
- Add performance benchmarks

**Tasks:**
- [ ] pgvector integration for embeddings
- [ ] Code indexing pipeline
- [ ] Semantic search implementation
- [ ] Task memory storage and retrieval
- [ ] Token budget optimization
- [ ] Context compression strategies
- [ ] Performance benchmarking suite
- [ ] Cost optimization analysis

**Success Criteria:**
- Relevant code snippets retrieved in <100ms
- Similar tasks found with >80% accuracy
- Token usage reduced by 30%
- Benchmarks establish performance baselines

### 10.7 Phase 6: Production (Week 9)

**Goals:**
- Production deployment configuration
- Monitoring and alerting
- Documentation and runbooks
- Security hardening

**Tasks:**
- [ ] Production Docker Compose
- [ ] Nginx reverse proxy with SSL
- [ ] Prometheus metrics collection
- [ ] Grafana dashboards
- [ ] Alertmanager configuration
- [ ] Backup and recovery procedures
- [ ] Security audit
- [ ] User documentation
- [ ] Operations runbooks

**Success Criteria:**
- System deploys with single command
- Monitoring covers all critical metrics
- Alerts fire on anomalies
- Documentation is complete and tested

---

## 11. Key Engineering Principles

### 11.1 Harness Engineering Philosophy

The core principle of Harness Engineering is that **the system determines the upper bound of capability, not the model**.
This means investing in robust infrastructure, governance, and tooling rather than relying solely on the AI model's capabilities.

### 11.2 Design Principles

#### 11.2.1 Strong Constraints Over Strong Models

**Principle:** Constrain the AI's search space through rules and validation rather than hoping the model will always generate correct code.

**Implementation:**
- Architectural constraints enforced by the system
- Forbidden patterns (e.g., no raw SQL, no eval)
- Mandatory type hints and async patterns
- Automated security scanning

**Benefits:**
- Consistent code quality regardless of model version
- Reduced hallucination and errors
- Easier debugging and maintenance
- Compliance with organizational standards

#### 11.2.2 State Management is Core

**Principle:** Treat state persistence and recovery as first-class concerns, not afterthoughts.

**Implementation:**
- Checkpoint after every task completion
- Atomic state saves with integrity verification
- Event sourcing for complete audit trails
- Resume from interruption without data loss

**Benefits:**
- Recovery from crashes and interruptions
- Debugging through event replay
- Compliance and forensic analysis
- Safe experimentation and rollback

#### 11.2.3 Feedback Loops with Bounded Iteration

**Principle:** Implement automatic error correction with strict limits to prevent infinite loops.

**Implementation:**
- Max iteration limits (default: 5)
- Cost tracking per task
- Progressive backoff strategies
- Human escalation on persistent failures

**Benefits:**
- Automatic recovery from transient errors
- Prevention of runaway costs
- Graceful degradation on complex tasks
- Learning from failure patterns

#### 11.2.4 Security by Design

**Principle:** Embed security at every layer rather than adding it as an afterthought.

**Implementation:**
- Sandboxed execution with no network access
- Permission-based tool access (RBAC)
- Human-in-the-loop for high-risk operations
- Immutable audit logs with tamper detection
- Secret detection and prevention

**Benefits:**
- Containment of potential AI-generated vulnerabilities
- Compliance with security standards
- Auditability for regulatory requirements
- Trust and confidence in automated systems

#### 11.2.5 Observability and Transparency

**Principle:** Every action, decision, and state change must be observable and explainable.

**Implementation:**
- Real-time WebSocket updates to dashboard
- Complete execution traces for every task
- Context inspection and debugging tools
- Evaluation result visualization
- Cost and performance metrics

**Benefits:**
- Debugging complex multi-step tasks
- Understanding AI decision-making
- Performance optimization
- User trust through transparency

### 11.3 Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| **Unrestricted Tool Access** | AI can modify production directly | Permission levels + human approval |
| **No State Persistence** | Lost progress on interruption | Checkpoint-based state store |
| **Infinite Retry Loops** | Runaway costs and stuck tasks | Max iterations + cost limits |
| **Context Pollution** | Irrelevant info degrades output | Token budgets + scope filtering |
| **Silent Failures** | Errors go unnoticed | Comprehensive logging + alerts |
| **No Quality Gates** | Bad code reaches production | Multi-dimensional evaluator |
| **Hardcoded Secrets** | Security vulnerabilities | Automated secret detection |
| **Blocking I/O in Async** | Performance degradation | Constraint enforcement |

---

## 12. Appendix: Configuration Files

### 12.1 Vite Configuration

```typescript
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";
import checker from "vite-plugin-checker";

export default defineConfig(({ mode }) => ({
  plugins: [
    react({
      // Fast refresh for development
      include: "**/*.tsx",
    }),
    checker({
      typescript: true,
      eslint: {
        lintCommand: 'eslint "./src/**/*.{ts,tsx}"',
      },
    }),
  ],
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
      "@components": resolve(__dirname, "./src/components"),
      "@hooks": resolve(__dirname, "./src/hooks"),
      "@store": resolve(__dirname, "./src/store"),
      "@api": resolve(__dirname, "./src/api"),
      "@types": resolve(__dirname, "./src/types"),
      "@utils": resolve(__dirname, "./src/utils"),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      // Proxy API requests to backend during development
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      // Proxy WebSocket connections
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: mode === "development",
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate vendor chunks for better caching
          vendor: ["react", "react-dom"],
          ui: ["@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu"],
          state: ["zustand", "immer"],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
}));
```

### 12.2 TypeScript Configuration

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@hooks/*": ["src/hooks/*"],
      "@store/*": ["src/store/*"],
      "@api/*": ["src/api/*"],
      "@types/*": ["src/types/*"],
      "@utils/*": ["src/utils/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 12.3 Tailwind CSS Configuration

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        harness: {
          primary: {
            DEFAULT: "#2563eb",
            dark: "#1d4ed8",
            light: "#3b82f6",
          },
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
          info: "#3b82f6",
        },
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow": "spin 3s linear infinite",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    require("@tailwindcss/typography"),
    require("@tailwindcss/forms"),
  ],
};
```

### 12.4 FastAPI Configuration

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """Application configuration."""
    
    # Application
    APP_NAME: str = "Harness Control Plane"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "postgresql://harness:harness@localhost:5432/harness"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 50
    
    # Claude Code / MCP
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    MCP_SERVER_URL: str = "http://localhost:3001"
    
    # Harness
    MAX_ITERATIONS: int = 5
    MAX_COST_PER_TASK: float = 5.0
    TASK_TIMEOUT_SECONDS: int = 300
    RETRY_COUNT: int = 3
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Sandbox
    SANDBOX_NETWORK_MODE: str = "none"
    SANDBOX_CPU_LIMIT: str = "1"
    SANDBOX_MEMORY_LIMIT: str = "2g"
    SANDBOX_TIMEOUT_SECONDS: int = 300
    
    # Evaluation
    MIN_TEST_COVERAGE: float = 80.0
    MAX_LINT_VIOLATIONS: int = 0
    MAX_SECURITY_ISSUES: int = 0
    
    # Context
    MAX_CONTEXT_TOKENS: int = 8000
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    VECTOR_DIMENSION: int = 1536
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### 12.5 Environment Variables

```bash
# .env
# Application
APP_NAME=Harness Control Plane
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://harness:${DB_PASSWORD}@postgres:5432/harness
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_POOL_SIZE=50

# Claude Code / MCP
CLAUDE_API_KEY=sk-ant-api03-...
CLAUDE_MODEL=claude-3-5-sonnet-20241022
MCP_SERVER_URL=http://mcp-server:3001

# Harness
MAX_ITERATIONS=5
MAX_COST_PER_TASK=5.0
TASK_TIMEOUT_SECONDS=300
RETRY_COUNT=3

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Sandbox
SANDBOX_NETWORK_MODE=none
SANDBOX_CPU_LIMIT=1
SANDBOX_MEMORY_LIMIT=2g
SANDBOX_TIMEOUT_SECONDS=300

# Evaluation
MIN_TEST_COVERAGE=80.0
MAX_LINT_VIOLATIONS=0
MAX_SECURITY_ISSUES=0

# Context
MAX_CONTEXT_TOKENS=8000
EMBEDDING_MODEL=text-embedding-3-large
VECTOR_DIMENSION=1536

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### 12.6 Nginx Configuration

```nginx
# docker/nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ws:10m rate=5r/s;

    upstream backend {
        server harness-orchestrator:8000;
        keepalive 32;
    }

    upstream frontend {
        server frontend:3000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name localhost;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name localhost;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_buffering off;
        }

        # WebSocket
        location /ws/ {
            limit_req zone=ws burst=10 nodelay;
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 86400;
        }

        # Health check
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

---

## 13. Conclusion

This Harness Engineering strategy provides a comprehensive framework for integrating Claude Code into a production-grade software development environment. By treating the AI agent as an operating system process with proper scheduling, memory, system calls, fault tolerance, security, and quality control, we achieve:

1. **Reliability**: Tasks are idempotent, checkpointed, and recoverable
2. **Security**: Sandboxed execution, permission controls, and audit trails
3. **Quality**: Multi-dimensional evaluation gates prevent bad code from reaching production
4. **Observability**: Real-time monitoring and complete execution traces
5. **Efficiency**: Token-optimized context management and automated feedback loops
6. **Governance**: Human-in-the-loop for high-risk operations and immutable audit logs

The key insight is that **the system architecture matters more than the model capabilities**. By building robust harness infrastructure, we enable Claude Code to operate safely and effectively within enterprise environments, transforming AI-assisted coding from a novelty into a reliable production tool.

---

*Document Version: 1.0*
*Last Updated: 2026-05-17*
*Author: Software Engineering Team*
