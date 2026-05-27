"""
Per-project configuration loaded from .Hardness/config.yaml.

Enables each Claude Code project to have its own governance rules,
evaluation thresholds, and tool permissions.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_CONFIG: Dict[str, Any] = {
    "project": {
        "name": "unknown",
        "scope": "general",
    },
    "governance": {
        "forbidden_patterns": [
            "no_raw_sql",
            "no_eval_exec",
            "no_hardcoded_secrets",
            "no_blocking_io_in_async",
        ],
        "require_approval_for": [],
    },
    "evaluation": {
        "test_coverage_min": 80,
        "lint_max_violations": 0,
        "security_max_critical": 0,
    },
    "tools": {
        "disabled": [],
    },
}


def find_project_root(start_path: Optional[str] = None) -> Path:
    """Walk up from start_path to find a .Hardness/ directory."""
    current = Path(start_path or os.getcwd()).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".Hardness").is_dir():
            return parent
    return Path(os.getcwd()).resolve()


def load_project_config(project_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Load project configuration from .Hardness/config.yaml.
    Falls back to env var Hardness_PROJECT_ROOT, then walks up from CWD.
    Merges with DEFAULT_CONFIG so all keys have sensible defaults.
    """
    root = project_root or os.environ.get("Hardness_PROJECT_ROOT")
    root_path = find_project_root(root) if root else find_project_root()

    config = dict(DEFAULT_CONFIG)
    config["project"]["name"] = root_path.name

    config_file = root_path / ".Hardness" / "config.yaml"
    if config_file.exists():
        try:
            with open(config_file, encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            _deep_merge(config, user_config)
        except Exception:
            pass

    return config


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base in place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_disabled_tools(project_root: Optional[str] = None) -> list:
    """Return list of tool names disabled for this project."""
    config = load_project_config(project_root)
    return config.get("tools", {}).get("disabled", [])
