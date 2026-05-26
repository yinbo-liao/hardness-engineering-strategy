# Hardness Engineering Skill

Use the Hardness MCP server tools whenever you need to ensure code quality, governance compliance, or task planning.

## Available Tools

- **read_file** — Read file contents from the workspace
- **write_file** — Write or modify source files
- **search_code** — Search the codebase for patterns
- **run_tests** — Execute the test suite with coverage reporting
- **run_linter** — Run code quality checks (ruff, mypy, black)
- **run_security_scan** — Run security analysis (bandit, semgrep)
- **evaluate_code** — Multi-dimensional quality evaluation

## Prompts

- Use `/hardness/plan-task` to decompose complex tasks into executable steps
- Use `/hardness/review-code` to check code against governance constraints
- Use `/hardness/evaluate` after generating code to validate quality

## Governance Rules (enforced by Hardness)

1. No raw SQL without parameterization — use SQLAlchemy ORM
2. No eval() or exec() in any context
3. No hardcoded credentials or secrets — use environment variables
4. No blocking I/O in async functions — use async/await
5. All Python functions must have type hints
6. Generated code must include tests (80% coverage minimum)
7. No circular imports

## Project Configuration

Per-project settings are in `.hardness/config.yaml`. Run `Hardness init` to create one.

## Quick Start

```bash
# Initialize Hardness in your project
Hardness init --scope api

# Start the MCP server (Claude Code will connect automatically)
Hardness serve --port 8900

# Run constraint checks manually
Hardness check

# Run performance benchmarks
Hardness bench
```
