# Hardness Engineering — User Guidance

## What is Hardness Engineering?

Hardness Engineering transforms Claude Code from an interactive coding assistant into a **managed, governable, and recoverable agent**. Instead of chatting with Claude, you submit tasks to a control plane that:

- Decomposes work into ordered tasks (DAG)
- Supplies optimized context with token budgets
- Enforces security constraints and permissions
- Evaluates results across 6 quality dimensions
- Recovers from failures with checkpointing
- Provides real-time visibility via WebSocket dashboard

**Core principle:** The system determines the upper bound of capability, not the model.

---

## Quick Start

### Prerequisites

- Python 3.11+, Node.js 22+, Docker Desktop
- PostgreSQL 16 (or use the Docker Compose setup)
- A Claude API key

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone git@github.com:yinbo-liao/hardness-engineering-strategy.git
cd hardness-engineering-strategy

# 2. Set up environment
cp .env.example .env
# Edit .env — set CLAUDE_API_KEY and a strong SECRET_KEY

# 3. Start the full stack
docker-compose -f docker-compose.hardness.yml up -d

# 4. Verify
curl http://localhost:8000/health
# → {"status": "healthy", "app": "Hardness Control Plane", "version": "1.0.0"}

# 5. Open the dashboard
# http://localhost:3000
```

### Development Setup (no Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev                  # Opens http://localhost:3000
```

---

## Core Concepts

### Task Lifecycle

```
Submitted → Queued → Running → (Evaluated) → Completed/Failed
                ↑                         ↓
                └──── Retry (max 3) ←─────┘
```

Each task goes through the Agent Loop (max 5 iterations):

```
Reason → Action → Execute → Evaluate → Feedback → (repeat or complete)
```

### Permission Levels

| Level | Can Do | Examples |
|-------|--------|----------|
| **READ** | Read files, search codebase | `read_file`, `search_code` |
| **WRITE** | Modify files, generate code | `write_file`, `generate_api` |
| **EXECUTE** | Run tests, linters, security scans | `run_tests`, `run_linter` |
| **DEPLOY** | Deploy to staging/production | `deploy_staging` (requires approval) |
| **ADMIN** | System configuration | `modify_ci_cd`, `manage_secrets` |

### Evaluation Dimensions

Each completed task is scored across 6 dimensions:

| Dimension | Tool | Threshold | Weight |
|-----------|------|-----------|--------|
| Unit Tests | pytest | ≥80% coverage, 0 failures | 25% |
| Type Safety | mypy | 0 errors | 20% |
| Code Style | ruff/black | 0 violations | 15% |
| Security | bandit/semgrep | 0 critical issues | 25% |
| Architecture | custom | No circular deps | 10% |
| Performance | benchmark | Within 10% of baseline | 5% |

**Overall pass requires**: All 3 critical dimensions pass (Tests, Security, Type Safety) AND weighted score ≥ 85%.

---

## Using the Dashboard

### Submitting a Task

1. Open http://localhost:3000
2. In the **New Task** panel, describe what you want to build:
   ```
   Add a FastAPI endpoint for user login with JWT authentication
   ```
3. Select a task type: **Code** / **Test** / **Review** / **Deploy** / **Fix**
4. Click **Submit Task** (or Ctrl+Enter)

### Monitoring Tasks

- **Task List** (left panel): All tasks with status badges and progress bars
- **Agent Loop Visualizer** (right panel, select a task): See the current phase (Reason → Action → Execute → Evaluate → Feedback) in real-time
- **Evaluation Results**: After completion, see per-dimension pass/fail and scores

### Handling Approvals

High-risk actions (deployments, configuration changes) require human approval:

1. Switch to the **Approvals** tab
2. Review the action, risk level, and parameters
3. Click **Approve** or **Reject**

Approvals time out after 5 minutes with a default deny.

### Audit Trail

The right panel shows an audit log of all actions, filterable by task. Every tool invocation, constraint violation, and approval decision is recorded with tamper-evident hashing.

---

## API Reference

### Submit a Task

```bash
curl -X POST http://localhost:8000/api/v1/Hardness/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "description": "Add user authentication with OAuth2 JWT tokens",
    "task_type": "code",
    "dependencies": [],
    "priority": 5,
    "timeout_seconds": 300
  }'
```

### Check Task Status

```bash
curl http://localhost:8000/api/v1/Hardness/tasks/task_abc123 \
  -H "Authorization: Bearer <token>"
```

### Query Audit Log

```bash
curl "http://localhost:8000/api/v1/Hardness/audit?session_id=session_abc&limit=50" \
  -H "Authorization: Bearer <token>"
```

### List Pending Approvals

```bash
curl http://localhost:8000/api/v1/Hardness/approvals \
  -H "Authorization: Bearer <token>"
```

### Approve / Deny

```bash
curl -X POST http://localhost:8000/api/v1/Hardness/approvals/apr_xyz/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"comment": "Reviewed and approved", "approver": "admin"}'
```

All errors follow RFC 7807 Problem Details format with `type`, `title`, `status`, `detail`, and `instance` fields.

---

## Security Constraints

The system enforces these rules — violations block task execution:

| Rule | Severity | What it Checks |
|------|----------|---------------|
| No raw SQL | CRITICAL | String concatenation in queries |
| No hardcoded secrets | CRITICAL | Passwords, API keys, tokens in code |
| No blocking I/O | HIGH | `requests.get`, `open()`, `time.sleep` in async |
| Type safety | MEDIUM | Missing type hints on functions |
| Test coverage | HIGH | New code must have test files |
| No circular imports | MEDIUM | Module dependency cycles |

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v          # All 155 tests
python -m pytest tests/test_planner.py -v   # Single module
python -m pytest tests/ -q --tb=short      # Quiet with short tracebacks
```

---

## Production Deployment

```bash
# Production stack includes Prometheus, Grafana, Alertmanager
docker-compose -f docker-compose.hardness.yml -f docker-compose.prod.yml up -d

# Access services:
# Dashboard:    https://your-host  (HTTP redirects to HTTPS)
# Grafana:      http://your-host:3001  (admin/admin)
# Prometheus:   http://your-host:9090  (internal only)
# API:          https://your-host/api/v1/Hardness/...
```

### Monitoring

- **Grafana dashboard**: Pre-configured with task metrics, agent loop iterations, cost tracking, approval queue depth
- **Alertmanager**: Routes critical alerts to Slack, all alerts to the Hardness webhook endpoint
- **Metrics endpoint**: `/metrics` exposes Prometheus-format metrics
- **Health check**: `/health` for load balancer readiness

### Backups

The `BackupManager` in `backend/app/hardness/backup.py` provides:

```python
from backend.app.hardness.backup import BackupManager

backup = BackupManager()

# Create a full backup
result = await backup.create_full_backup(label="pre-deploy")
# → /data/backups/hardness_backup_pre-deploy_20260518_120000.sql.gz

# Clean up backups older than 7 days
removed = await backup.cleanup_old_backups(keep_days=7)

# List recent backups
backups = await backup.list_backups()
```

### Security Audit

```python
from backend.app.hardness.security_audit import SecurityAuditor

auditor = SecurityAuditor(root_path=".")
report = await auditor.run_all()

print(f"Findings: {report.summary['total']}")
print(f"Critical: {report.summary['critical']}")
print(f"Passed: {report.passed}")
```

---

## Using with Claude Code

The Hardness CLI acts as a Claude Code plugin via MCP (Model Context Protocol). Once configured, Claude Code can invoke Hardness tools for code review, security scanning, test execution, and quality evaluation — all within your normal Claude Code sessions.

### Install the CLI

```bash
cd hardness-engineering-strategy/backend
pip install -e .           # Installs the `Hardness` CLI command

# Verify installation
Hardness --help
```

### Initialize a Project

```bash
# From your project root, create a .hardness/ config directory
Hardness init --scope api    # options: api, ui, db, infra, test, security, general
```

This creates `.hardness/config.yaml` with governance rules, evaluation thresholds, and tool permissions for your project.

### Configure Claude Code

Add the Hardness MCP server to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "hardness": {
      "type": "http",
      "url": "http://127.0.0.1:8900/mcp"
    }
  }
}
```

Or use the Claude Code `/config` command to add it interactively.

### Start the MCP Server

```bash
# Start in the foreground (default port 8900)
Hardness serve

# Start on a custom port with debug logging
Hardness serve --port 8901 --debug

# Start from a specific project directory
Hardness serve --project /path/to/your/project
```

The server exposes a JSON-RPC 2.0 endpoint at `http://127.0.0.1:8900/mcp`. Claude Code will automatically discover available tools on connection.

### Available Tools in Claude Code

Once connected, these tools become available to Claude Code:

| Tool | Permission | Description |
|------|-----------|-------------|
| `read_file` | READ | Read file contents from the workspace |
| `write_file` | WRITE | Write or modify source files |
| `search_code` | READ | Search the codebase by pattern |
| `run_tests` | EXECUTE | Run pytest with coverage reporting |
| `run_linter` | EXECUTE | Run ruff + mypy + black checks |
| `run_security_scan` | EXECUTE | Run bandit + semgrep analysis |
| `evaluate_code` | EXECUTE | Multi-dimensional quality evaluation |

### Slash Commands (Prompts)

Use these prompts within Claude Code:

| Command | What it Does |
|---------|-------------|
| `/Hardness/plan-task` | Decompose a complex request into a DAG of executable tasks |
| `/Hardness/review-code` | Check code against governance constraints and flag violations |
| `/Hardness/evaluate` | Run full 6-dimension evaluation on recently generated code |

### How Governance Works

When you ask Claude Code to generate or modify code, the Hardness plugin enforces constraints automatically:

1. **Pre-execution**: Tool parameters are validated against constraint rules
2. **Post-execution**: Generated code is checked for secrets, SQL injection, blocking I/O, missing type hints
3. **Evaluation gate**: Run `/Hardness/evaluate` to score code across all 6 quality dimensions

If a constraint violation is found (e.g., a hardcoded secret), the tool call is blocked before any file is written.

### Example Workflow

```bash
# 1. Start the MCP server in one terminal
Hardness serve

# 2. In another terminal (or Claude Code), start a session
claude

# 3. Within Claude Code:
# "Review the current codebase for security issues"
# → Claude calls run_security_scan via Hardness MCP
#
# "Add a FastAPI endpoint for user logout"
# → Claude generates code, then you run /Hardness/evaluate
# → 6-dimension quality report appears inline
```

---

## Troubleshooting

### Task stuck in "running" state

1. Check the Agent Loop Visualizer for the current phase
2. Review the task's error log via `GET /api/v1/Hardness/tasks/{task_id}`
3. If at max iterations (5), the task will auto-fail — submit a new task with more specific instructions
4. For sandbox issues, check Docker logs: `docker logs hardness-sandbox`

### WebSocket disconnects

The dashboard automatically reconnects with exponential backoff (up to 5 attempts). If persistent:
1. Check the orchestrator is running: `docker logs hardness-orchestrator`
2. Verify the WebSocket URL in `.env` matches: `VITE_WS_URL=ws://localhost:8000`

### Tests are failing

1. Verify Python version: `python --version` (needs 3.11+)
2. Install all dependencies: `pip install -r backend/requirements.txt`
3. Run from the `backend/` directory
4. Check for import errors in individual test files

### Permission denied errors

1. Verify the JWT token includes the required permission level
2. Check the RBAC middleware exempt paths in `backend/app/main.py`
3. For development, set `DEBUG=true` in `.env` to expose `/docs` endpoint

---

## Architecture at a Glance

```
User Request → [Task Planner: DAG decomposition]
                    ↓
              [Context Manager: 4-layer context assembly]
                    ↓
              [Orchestrator: Agent Loop]
                    ↓
         ┌─────────┼─────────┐
         ↓         ↓         ↓
    [MCP Client] [Tool Registry] [Evaluator]
         ↓         ↓         ↓
    Claude Code   Sandbox   6-dimension
                 (Docker)    scoring
                    ↓
              [Governance: constraints + audit]
                    ↓
              [State Store: checkpoint + recovery]
```

---

*Document version: 1.1 — Last updated: 2026-05-27*
