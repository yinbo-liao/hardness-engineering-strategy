"""Hook handlers for Claude Code settings.json hooks.

Each function is designed to be called from a Claude Code hook configuration.
They return JSON-serializable dicts for machine consumption.
"""

import json
import sys
from pathlib import Path


def post_write_check(file_path: str, scope: str = "auto") -> dict:
    """Run governance constraint check after a file write event.

    Called by PostToolUse hook on Write/Edit tools.
    Returns a dict with 'passed' and 'violations' keys.
    """
    from hardness_plugin.governance import Governance
    from hardness_plugin.project_config import load_project_config

    gov = Governance()

    try:
        config = load_project_config()
    except Exception:
        config = {}

    task_scope = scope if scope != "auto" else config.get("project", {}).get("scope", "general")

    fp = Path(file_path)
    try:
        content = fp.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return {"passed": True, "violations": [], "error": f"Cannot read {file_path}"}

    result = gov.check_constraint(
        action="write_file",
        params={"file_path": str(fp), "content": content},
        task_scope=task_scope,
    )

    return {
        "passed": result["passed"],
        "file": str(fp),
        "violations": [
            {"rule": v["rule"], "severity": v["severity"], "message": v["message"]}
            for v in result.get("violations", [])
        ],
    }


def pre_push_check(project_root: str = ".") -> dict:
    """Run full security-focused check before git push.

    Called by PreToolUse hook on Bash(git push*) commands.
    Scans all Python/Typescript/SQL files for security violations.
    """
    from hardness_plugin.governance import Governance

    gov = Governance()
    root = Path(project_root).resolve()
    violations_found = []

    exclude = {".git", "node_modules", "__pycache__", ".venv", "venv", ".hardness"}
    for ext in (".py", ".ts", ".tsx", ".js", ".sql"):
        for fp in root.rglob(f"*{ext}"):
            if any(p in fp.parts for p in exclude):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue
            result = gov.check_constraint(
                "write_file",
                {"file_path": str(fp), "content": content},
                "security",
            )
            if not result["passed"]:
                for v in result.get("violations", []):
                    v["file"] = str(fp)
                    violations_found.append(v)

    return {
        "passed": len(violations_found) == 0,
        "violations_count": len(violations_found),
        "violations": violations_found,
    }


def evaluate_file(file_path: str) -> dict:
    """Run quality evaluation on a specific file.

    Called on-demand for detailed quality scoring.
    """
    from hardness_plugin.evaluator import evaluate_code_quality

    fp = Path(file_path)
    try:
        content = fp.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return {"error": f"Cannot read {file_path}"}

    return evaluate_code_quality(str(fp), content)
