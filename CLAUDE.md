# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Harness Engineering** system — a control plane that transforms Claude Code from an interactive coding assistant into a managed, governable, recoverable agent. The master blueprint is `harness_engineering_strategy.md`.

## Core Philosophy

> **"The system (Harness) determines the upper bound of capability, not the model."**

## Commands

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000     # dev server

# Frontend (not yet implemented — Phase 3)
cd frontend
npm install
npm run dev                                           # Vite dev server on :3000

# Testing
cd backend
pytest tests/ -v                                      # all tests
pytest tests/test_planner.py -v                       # single test file

# Docker
docker-compose -f docker-compose.harness.yml up       # full stack
docker-compose -f docker-compose.harness.yml up -d    # detached

# Alembic
cd backend
alembic upgrade head                                  # apply migrations
alembic revision --autogenerate -m "description"      # new migration
```

## Project Structure

```
backend/
  app/
    main.py              # FastAPI entry point (lifespan, CORS, routes, /health)
    config.py            # Pydantic Settings (all env vars)
    harness/
      planner.py         # TaskPlanner: DAG + Kahn's topological sort, checkpoint recovery
      context_manager.py # ContextManager: 4-layer assembly with token budgets
      state_store.py     # StateStore: PG-backed checkpoints + event sourcing
      tool_registry.py
      governance.py
      orchestrator.py
      evaluator.py
      mcp_client.py
      sandbox.py
    api/v1/
      tasks.py           # POST /tasks, GET /tasks/{id}, GET /tasks
      audit.py           # GET /audit (query with filters)
      approvals.py       # POST /approvals/{id}/approve|deny
      ws.py              # WebSocket manager + /ws/main endpoint
    models/
      task.py            # SQLAlchemy: harness_tasks
      checkpoint.py      # SQLAlchemy: harness_checkpoints
      event.py           # SQLAlchemy: harness_events (event sourcing)
      audit.py           # SQLAlchemy: harness_audit_log
      embedding.py       # SQLAlchemy: code_embeddings (pgvector)
    db/session.py        # Async SQLAlchemy engine + session factory
  alembic/               # Database migrations
  tests/
    conftest.py          # async pytest fixtures
    test_planner.py      # DAG ordering, cycle detection, idempotency, checkpoint recovery
    test_context_manager.py # scope detection, token budgeting, context assembly
docker/
  harness-orchestrator.Dockerfile
  harness-sandbox.Dockerfile  # non-root user, seccomp, read-only root
  nginx/nginx.conf            # reverse proxy: /api→orchestrator, /→frontend, /ws→WS
  postgres/init/              # pgvector extension init
  seccomp-profile.json        # syscall whitelist for sandbox
  sandbox-policy.json         # sandbox security policy
frontend/                # (Phase 3) React + Vite + TypeScript
```

## Architecture (3 Layers)

**Control Plane**: Task Planner (DAG + topological sort) → Context Manager (4-layer context + token budget) → Governance & Audit (constraints, RBAC, human-in-the-loop)

**Orchestration Layer**: MCP Server → Agent Loop (Reason→Action→Execute→Evaluate→Feedback, max 5 iterations)

**Execution Environment**: Sandboxed Docker containers (`network_mode: none`, read-only rootfs, seccomp, non-root user, resource limits)

## Design Principles

- **Strong Constraints Over Strong Models** — System-enforced rules, not model-requested. Forbidden: raw SQL, `eval()`/`exec()`, hardcoded secrets, blocking I/O in async, circular imports
- **State Management is Core** — Atomic checkpoint saves, event sourcing, resume from interruption
- **Bounded Feedback Loops** — Max 5 iterations, cost tracking, human escalation on failure
- **Security by Design** — Sandboxed exec, RBAC, tamper-evident audit logs, secret detection
- **Observability** — Real-time WebSocket updates, complete execution traces

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+), SQLAlchemy 2.0 async, Pydantic v2 |
| Frontend | React 18+ + TypeScript 5 (strict), Vite 5, Tailwind CSS 3, Zustand |
| Agent | Claude Code via MCP, WebSocket |
| State | PostgreSQL + pgvector, Redis |
| Infra | Docker + Docker Compose, Nginx, Prometheus + Grafana |

## API Conventions

- REST versioning via URL path (`/api/v1/...`)
- RFC 7807 Problem Details for errors
- Bearer JWT in Authorization header
- WebSocket: JSON messages, 30s ping/pong heartbeat, exponential backoff reconnection

## Coding Standards

- **Python**: PEP8, mandatory type hints, async/await for all I/O, absolute imports, Google-style docstrings
- **TypeScript**: strict mode, functional components + hooks, Zod for API validation, Zustand + React Query

## Implementation Status

- [x] Phase 1: Foundation — 39 files, 28 tests
- [x] Phase 2: Integration — 6 harness modules, 3 schema modules, 35 new tests (63 total)
- [x] Phase 3: Frontend — Vite + React + TypeScript dashboard, 14 components, Zustand store, WebSocket hook, API client
- [x] Phase 4: Governance — Circular imports detection, test coverage checks, notification service (Slack/email), rate limiting middleware, RBAC/JWT middleware, RFC 7807 error handling, 25 new tests (88 total)
- [x] Phase 5: Optimization — CodeIndexer + SemanticSearcher (pgvector RAG), TaskMemoryStore (similarity retrieval, tag index, LRU eviction), BenchmarkRunner (p50/p95/p99 percentiles, cost tracking), TokenOptimizer (compression, dedup, budget enforcement), 44 new tests (132 total)
- [x] Phase 6: Production — MetricsCollector (Prometheus), SecurityAuditor (secrets/deps/container/network), BackupManager (pg_dump/restore), production docker-compose, Nginx SSL/TLS, Grafana dashboard, Alertmanager, 23 new tests (155 total)
