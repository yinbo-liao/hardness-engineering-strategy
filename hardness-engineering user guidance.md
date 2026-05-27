# Hardness Engineering — User Guidance

## What is Hardness Engineering?

Hardness Engineering is a **Claude Code plugin** that enforces code quality, security, and governance constraints directly within your Claude Code sessions. It runs as a lightweight Python package — no servers, no databases, no Docker.

**How it works:**

- **Hooks** automatically check your code after every file write for secrets, SQL injection, blocking I/O, and other violations
- **Slash commands** let you manually trigger evaluation, planning, and constraint checks
- **A subagent** can be invoked for deep governance reviews

**Core principle:** "The system (Hardness) determines the upper bound of capability, not the model."

---

## Quick Start

### Prerequisites

- Python 3.11+
- Claude Code (desktop app or CLI)

### Installation

```bash
# Clone and install
git clone git@github.com:yinbo-liao/hardness-engineering-strategy.git
cd hardness-engineering-strategy
pip install -e ".[dev]"

# Verify
hardness --help
```

No Docker, no database, no Node.js required.

### Initialize Your Project

```bash
# Create per-project configuration
hardness init --scope api    # Options: api, ui, db, infra, test, security, general
```

This creates `.hardness/config.yaml` with governance rules and evaluation thresholds.

---

## Using the Plugin

### Slash Commands in Claude Code

Open a Claude Code session in your project and use:

| Command | What it Does |
|---------|-------------|
| `/hardness:check` | Run governance constraint checks on changed files |
| `/hardness:evaluate` | Multi-dimensional quality evaluation of generated code |
| `/hardness:plan` | Decompose a complex task into DAG execution steps |
| `/hardness:init` | Initialize `.hardness/config.yaml` for the current project |

### CLI Commands

```bash
# Check your code against governance rules
hardness check --path .
hardness check --files src/auth.py --json    # Machine-readable output

# Evaluate code quality (6 dimensions)
hardness evaluate --path src/
hardness evaluate --path src/ --json

# Plan a complex task
hardness plan "Add user authentication with JWT and refresh tokens"

# Run performance benchmarks
hardness bench --iterations 20

# Session metrics
hardness metrics --render
```

### Automatic Hook Enforcement

Once the plugin is installed and `.claude/settings.json` is present, Hardness runs automatically:

- **After every Write/Edit** — governance constraint check on the modified file
- **Before git push** — full security scan across all project files
- **Session start** — ensures `.hardness/config.yaml` exists

No manual invocation needed for standard workflows.

---

## Core Concepts

### Governance Rules

Seven constraint rules are enforced deterministically (regex/pattern matching, no LLM):

| Rule | Severity | What it Checks |
|------|----------|---------------|
| **no_raw_sql** | CRITICAL | String concatenation or f-strings in SQL queries |
| **no_eval_exec** | CRITICAL | `eval()` or `exec()` calls in code |
| **no_hardcoded_secrets** | CRITICAL | Passwords, API keys, tokens hardcoded in source |
| **no_blocking_io_in_async** | HIGH | `requests.get`, `open()`, `time.sleep` in async context |
| **type_safety** | MEDIUM | Missing type hints on Python functions |
| **test_coverage** | HIGH | New code must include or reference tests |
| **no_circular_imports** | MEDIUM | Mutual import dependencies between modules |

### Evaluation Dimensions

Code quality is assessed across 6 dimensions via static analysis:

| Dimension | Weight | What it Checks |
|-----------|--------|---------------|
| **Unit Tests** | 25% | Test patterns, asserts, test file detection |
| **Type Safety** | 20% | Type hints on functions and variables |
| **Lint** | 15% | Tabs, trailing whitespace, line length |
| **Security Scan** | 25% | Secrets, SQL injection, eval/exec |
| **Architecture** | 10% | Circular dependency indicators |
| **Performance** | 5% | `range(len())`, `time.sleep` patterns |

**Overall pass requires**: All 3 critical dimensions pass (Tests, Security, Type Safety) AND weighted score >= 70%.

### Permission Levels (Tool Registry)

When using the `tool_registry` module programmatically:

| Level | Can Do | Examples |
|-------|--------|----------|
| **READ** | Read files, search codebase | `read_file`, `search_code` |
| **WRITE** | Modify files, generate code | `write_file`, `generate_api` |
| **EXECUTE** | Run tests, linters, security scans | `run_tests`, `run_linter` |
| **DEPLOY** | Deploy to staging/production | requires human approval |
| **ADMIN** | System configuration | restricted operations |

### Task Planning (DAG)

For complex multi-step tasks, decompose work into a DAG with topological ordering:

```python
from hardness_plugin.planner import TaskPlanner, TaskNode

planner = TaskPlanner()
planner.add_task(TaskNode(id="step-1", description="Set up project structure"))
planner.add_task(TaskNode(id="step-2", description="Add auth endpoints", deps=["step-1"]))
planner.add_task(TaskNode(id="step-3", description="Add tests", deps=["step-2"]))

order = planner.get_execution_order()  # ['step-1', 'step-2', 'step-3']
```

---

## Plugin Architecture

```
Claude Code Session
    |
    ├── Hooks (.claude/settings.json)
    |   ├── PostToolUse (Write/Edit) -> hardness check --files <file>
    |   ├── PreToolUse (git push)    -> hardness check --scope security
    |   └── SessionStart             -> hardness init --if-missing
    |
    ├── Skills (.claude/skills/hardness.md)
    |   └── Slash commands: /hardness:check, /hardness:evaluate, /hardness:plan
    |
    └── Agents (.claude/agents/hardness-governor.md)
        └── Governance subagent for deep review
```

### Python Package Structure

```
hardness_plugin/
├── governance.py        # Constraint engine (7 rules, audit, approval)
├── planner.py           # DAG task planner with topological sort
├── tool_registry.py     # 8-step controlled tool pipeline
├── evaluator.py         # 6-dimension quality assessment (static analysis)
├── token_optimizer.py   # Token budget management
├── task_memory.py       # In-memory solution store with similarity search
├── project_config.py    # Per-project YAML config (.hardness/config.yaml)
├── benchmarks.py        # Performance benchmark runner
├── metrics.py           # Prometheus-format metrics collector
├── cli.py               # Typer CLI entry point
├── hooks.py             # Hook handler functions
└── __init__.py          # Public API re-exports
```

### Dependencies

Only 4 packages: `pydantic`, `typer`, `rich`, `pyyaml`. No database, no web framework, no Docker.

---

## Per-Project Configuration

### `.hardness/config.yaml`

```yaml
project:
  name: my-project
  scope: api              # api, ui, db, infra, test, security, general

governance:
  forbidden_patterns:
    - no_raw_sql
    - no_eval_exec
    - no_hardcoded_secrets
    - no_blocking_io_in_async
  require_approval_for: []

evaluation:
  test_coverage_min: 80
  lint_max_violations: 0
  security_max_critical: 0

tools:
  disabled: []
```

### `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "hardness check --files \"$CLAUDE_TOOL_INPUT_FILE_PATH\" --json",
        "timeout": 15000
      }]
    }],
    "PreToolUse": [{
      "matcher": "Bash\\(git push.*\\)",
      "hooks": [{
        "type": "command",
        "command": "hardness check --path . --scope security --json",
        "timeout": 30000
      }]
    }]
  }
}
```

---

## Programmatic Usage

### Import as a Python Library

```python
from hardness_plugin import Governance, evaluate_code_quality, TaskPlanner, TaskNode

# Run constraint checks
gov = Governance()
result = gov.check_constraint(
    "write_file",
    {"file_path": "src/auth.py", "content": 'password = "admin123"'},
    "api",
)
print(f"Passed: {result['passed']}")
print(f"Violations: {result['violations']}")

# Evaluate code quality
score = evaluate_code_quality("src/auth.py", file_content)
print(f"Weighted score: {score['weighted_score']}")

# Plan a task
planner = TaskPlanner()
planner.add_task(TaskNode(id="1", description="Create auth module"))
planner.add_task(TaskNode(id="2", description="Write tests", deps=["1"]))
order = planner.get_execution_order()  # ['1', '2']
```

### Hook Handlers

```python
from hardness_plugin.hooks import post_write_check, pre_push_check, evaluate_file

# After a file write
result = post_write_check("src/auth.py", scope="api")

# Before git push
result = pre_push_check(".")

# Detailed file evaluation
result = evaluate_file("src/auth.py")
```

---

## Using the Governance Subagent

When you need a thorough governance review, invoke the subagent within Claude Code:

```
/invoke hardness-governor "Review all files under src/ for security violations"
```

The subagent scans Python/TypeScript/SQL files, runs automated analysis, and outputs a structured governance report with severity levels and fix suggestions.

---

## Scope Reference

Each governance rule applies to specific project scopes:

| Scope | Applies To | Active Rules |
|-------|-----------|-------------|
| **api** | Backend endpoints, FastAPI, REST APIs | no_blocking_io, type_safety, sql_injection_prevention, no_circular_imports, test_coverage |
| **ui** | Frontend components, React, CSS | type_safety, no_circular_imports, test_coverage |
| **db** | Database models, migrations, queries | no_blocking_io, sql_injection_prevention, test_coverage |
| **infra** | Docker, CI/CD, deployment configs | no_blocking_io, secret_detection |
| **test** | Test files, fixtures, mocks | type_safety |
| **security** | Auth, encryption, secrets management | All rules — no scope filtering |
| **general** | Catch-all (default) | Forbidden actions only (eval, exec) |
| **code** | General Python/TypeScript modules | type_safety, secret_detection, no_circular_imports, test_coverage |

---

## Example Workflow

Terminal session:

```bash
# 1. Initialize Hardness in your project
$ hardness init --scope api
Created .hardness/config.yaml

# 2. Claude generates code in Claude Code session
#    Claude writes: src/auth.py with JWT authentication

# 3. Plugin auto-checks the file (PostToolUse hook)
#    Behind the scenes: hardness check --files src/auth.py

# 4. Manually evaluate quality
$ hardness evaluate --path src/auth.py

# 5. Check governance before committing
$ hardness check --path src/
No violations in 3 file(s)

# 6. Commit and push
$ git add src/ && git commit -m "Add JWT auth module"
$ git push   # PreToolUse hook runs security scan before push
```

Within Claude Code:

```
/hardness:plan "Add JWT authentication with refresh tokens"
[Claude generates the implementation]

/hardness:evaluate
[Shows quality scores for generated files]

/hardness:check
[Verifies no constraint violations]
```

---

## Extending the Plugin

### Adding Custom Governance Rules

```python
from hardness_plugin.governance import Governance, ConstraintRule, RiskLevel

gov = Governance()

def check_no_todo_comments(params: dict) -> dict:
    content = params.get("content", "")
    todos = content.count("TODO") + content.count("FIXME")
    return {
        "passed": todos <= 3,
        "message": f"Found {todos} TODO/FIXME comments (max 3 allowed)",
        "suggestion": "Resolve or track TODOs before merging",
    }

gov.constraint_rules.append(
    ConstraintRule(
        id="no_excessive_todos",
        description="Limit TODO/FIXME comments to 3 per file",
        check_function=check_no_todo_comments,
        severity=RiskLevel.MEDIUM,
        scope=["code", "api", "ui"],
        auto_fix=False,
    )
)

result = gov.check_constraint("write_file", {"content": code}, "api")
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Hardness Check
on: [push, pull_request]

jobs:
  hardness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: hardness check --path . --scope security --json > report.json
      - name: Fail on violations
        run: |
          PASSED=$(python -c "import json; print(json.load(open('report.json'))['passed'])")
          if [ "$PASSED" != "True" ]; then
            echo "Governance violations found"; cat report.json; exit 1
          fi
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
hardness check --path . --scope api || {
    echo "Hardness check failed. Fix violations before committing."
    exit 1
}
```

---

## Testing

```bash
# Run all 92 tests
pytest tests/ -v

# Run specific module tests
pytest tests/test_governance.py -v
pytest tests/test_evaluator.py -v

# With coverage
pytest tests/ --cov=hardness_plugin --cov-report=term
```

---

## Troubleshooting

### Changes not being checked

1. Verify the plugin is installed: `hardness --help`
2. Check `.claude/settings.json` exists with hook configurations
3. Run manually: `hardness check --path .`

### Excessive false positives

1. Edit `.hardness/config.yaml` — remove rules from `governance.forbidden_patterns`
2. Use `--scope` to narrow checks: `hardness check --scope api`

### Module not found

```bash
pip install -e ".[dev]"
```

### Subagent not found

Verify `.claude/agents/hardness-governor.md` exists. Agent definitions load automatically when Claude Code opens the project.

### JSON output parsing

```bash
hardness check --files src/auth.py --json > report.json
python -c "import json; print(json.load(open('report.json')))"
```

---

*Document version: 2.1 — Last updated: 2026-05-27*
