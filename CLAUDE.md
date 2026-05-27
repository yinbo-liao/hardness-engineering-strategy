# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Repository Overview

This is the **Hardness Engineering** plugin for Claude Code — a governance, evaluation, and task planning toolkit that enforces code quality and security constraints within Claude Code sessions.

The master reference document is `Hardness_engineering_strategy.md`.

## Core Philosophy

> **"The system (Hardness) determines the upper bound of capability, not the model."**

## Commands

```bash
# Plugin CLI (all commands)
hardness --help

# Initialize per-project config
hardness init --scope api

# Run governance constraint checks
hardness check --path .
hardness check --files path/to/file.py
hardness check --path . --json       # machine-readable output

# Multi-dimensional quality evaluation
hardness evaluate --path src/
hardness evaluate --path src/ --json

# Task planning (DAG decomposition)
hardness plan "Add user authentication with JWT support"

# Performance benchmarks
hardness bench
hardness bench --iterations 20 --output results.json

# Session metrics
hardness metrics --increment files_checked
hardness metrics --render
```

## Plugin Structure

```
hardness_plugin/         # Python package
├── governance.py        # Constraint engine (6 rules, audit, approval)
├── planner.py           # DAG task planner with topological sort
├── tool_registry.py     # 8-step controlled tool pipeline
├── evaluator.py         # 6-dimension quality assessment (static analysis)
├── token_optimizer.py   # Token budget management
├── task_memory.py       # In-memory solution store with similarity search
├── project_config.py    # Per-project YAML config (.hardness/config.yaml)
├── benchmarks.py        # Performance benchmark runner
├── metrics.py           # Prometheus-format metrics collector
├── cli.py               # Typer CLI
├── hooks.py             # Hook handlers for settings.json
└── __init__.py
tests/                   # 92 unit tests (pytest)
.claude/
├── skills/hardness.md   # Plugin skill: slash commands + behaviors
├── agents/hardness-governor.md  # Governance subagent
└── settings.json        # Hooks (PostToolUse, PreToolUse, SessionStart)
.hardness/
└── config.yaml          # Project-specific governance/evaluation config
```

## Architecture

The plugin operates within Claude Code via three mechanisms:

1. **Hooks** (`.claude/settings.json`) — Automatically run `hardness check` on file writes and security scans before git push
2. **Skills** (`.claude/skills/hardness.md`) — Slash commands for manual governance checks, evaluation, and task planning
3. **Agents** (`.claude/agents/hardness-governor.md`) — Specialized subagent for governance constraint review

## Design Principles

- **Strong Constraints Over Strong Models** — Deterministic rule enforcement via static analysis, not LLM judgment
- **Zero Infrastructure** — No PostgreSQL, Redis, Docker, or web servers needed
- **File-Based Config** — Per-project `.hardness/config.yaml` for customization
- **Fast Execution** — Pure Python stdlib + minimal deps (pydantic, typer, rich, pyyaml)

## Testing

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests (92 currently)
pytest tests/ -v

# Run specific test file
pytest tests/test_governance.py -v

# Run with coverage
pytest tests/ --cov=hardness_plugin --cov-report=term
```

## Key Modules

| Module | Purpose | Dependencies |
|--------|---------|-------------|
| `governance.py` | 6 constraint rules + audit + human-in-the-loop approval | None |
| `planner.py` | DAG task decomposition, Kahn's topological sort, checkpoint recovery | None |
| `evaluator.py` | 6-dimension code quality scoring (static analysis) | None |
| `tool_registry.py` | 8-step tool call pipeline with permissions | Pydantic |
| `token_optimizer.py` | Token budget estimation, truncation, compression | None |
| `task_memory.py` | Solution memory with hash-based embeddings + cosine similarity | None |
| `project_config.py` | YAML config loader from `.hardness/config.yaml` | PyYAML |
