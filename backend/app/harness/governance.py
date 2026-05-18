import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Set


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ConstraintRule:
    id: str
    description: str
    check_function: Callable
    severity: RiskLevel
    scope: List[str] = field(default_factory=lambda: ["*"])
    auto_fix: bool = False


@dataclass
class AuditEntry:
    entry_id: str
    timestamp: str
    session_id: str
    action: str
    actor: str
    params: dict
    result: str
    risk_level: RiskLevel
    approval_required: bool = False
    approval_granted: Optional[bool] = None


class ConstraintViolation(Exception):
    pass


class SecurityViolation(Exception):
    pass


class Governance:
    """
    Constraint enforcement, audit logging, and human-in-the-loop approvals.

    Implements the principle: "Strong constraints > Strong model"
    By constraining the LLM's search space through rules, we improve
    consistency and reduce uncertainty.
    """

    def __init__(
        self,
        notification_service=None,
        approval_timeout_seconds: int = 300,
    ):
        self.forbidden_actions: Set[str] = {
            "delete_prod_db",
            "drop_table",
            "exec_shell_unrestricted",
            "modify_ci_cd",
            "access_secrets_vault",
            "disable_audit_logging",
            "modify_governance_rules",
        }

        self.constraint_rules = self._load_constraint_rules()
        self.audit_log: List[AuditEntry] = []
        self.pending_approvals: Dict[str, asyncio.Future] = {}
        self.notification_service = notification_service
        self.approval_timeout = approval_timeout_seconds
        self.approval_callbacks: Dict[str, Callable] = {}

    def _load_constraint_rules(self) -> List[ConstraintRule]:
        return [
            ConstraintRule(
                id="no_blocking_io",
                description="All I/O operations must be async",
                check_function=self._check_async_patterns,
                severity=RiskLevel.HIGH,
                scope=["api", "db", "infra"],
                auto_fix=False,
            ),
            ConstraintRule(
                id="type_safety",
                description="All functions must have type hints",
                check_function=self._check_type_hints,
                severity=RiskLevel.MEDIUM,
                scope=["code", "api", "ui"],
                auto_fix=True,
            ),
            ConstraintRule(
                id="sql_injection_prevention",
                description="No string concatenation in SQL",
                check_function=self._check_sql_safety,
                severity=RiskLevel.CRITICAL,
                scope=["db", "api"],
                auto_fix=False,
            ),
            ConstraintRule(
                id="secret_detection",
                description="No hardcoded secrets in generated code",
                check_function=self._check_secrets,
                severity=RiskLevel.CRITICAL,
                scope=["code", "config", "infra"],
                auto_fix=False,
            ),
            ConstraintRule(
                id="no_circular_imports",
                description="No circular import dependencies",
                check_function=self._check_circular_imports,
                severity=RiskLevel.MEDIUM,
                scope=["code", "api", "ui"],
                auto_fix=True,
            ),
            ConstraintRule(
                id="test_coverage",
                description="All new code must have tests",
                check_function=self._check_test_coverage,
                severity=RiskLevel.HIGH,
                scope=["code", "api", "ui", "db"],
                auto_fix=False,
            ),
        ]

    def check_constraint(
        self, action: str, params: dict, task_scope: str = "general"
    ) -> dict:
        violations: list = []

        if action in self.forbidden_actions:
            violations.append(
                {
                    "rule": "forbidden_action",
                    "severity": RiskLevel.CRITICAL.value,
                    "message": f"Action '{action}' is permanently forbidden",
                }
            )

        for rule in self.constraint_rules:
            if task_scope in rule.scope or "*" in rule.scope:
                try:
                    result = rule.check_function(params)
                    if not result["passed"]:
                        violations.append(
                            {
                                "rule": rule.id,
                                "severity": rule.severity.value,
                                "message": result["message"],
                                "auto_fixable": rule.auto_fix,
                                "suggestion": result.get("suggestion"),
                            }
                        )
                except Exception as e:
                    violations.append(
                        {
                            "rule": rule.id,
                            "severity": RiskLevel.HIGH.value,
                            "message": f"Constraint check failed: {e!s}",
                        }
                    )

        critical_count = sum(
            1 for v in violations if v["severity"] == RiskLevel.CRITICAL.value
        )

        return {
            "passed": critical_count == 0 and len(violations) < 3,
            "violations": violations,
            "can_proceed": critical_count == 0,
        }

    async def request_human_approval(
        self,
        action: str,
        params: dict,
        session_id: str,
        risk_level: str = "medium",
    ) -> bool:
        approval_id = (
            f"apr_{session_id}_{action}_"
            f"{int(time.time() * 1000)}"
        )

        request_data = {
            "approval_id": approval_id,
            "session_id": session_id,
            "action": action,
            "params": self._sanitize_for_display(params),
            "risk_level": risk_level,
            "requested_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            ),
            "timeout_at": time.time() + self.approval_timeout,
        }

        await self._send_approval_notification(request_data)

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.pending_approvals[approval_id] = future

        try:
            approved = await asyncio.wait_for(
                future, timeout=self.approval_timeout
            )
            self.audit(
                {
                    "approval_id": approval_id,
                    "action": action,
                    "session_id": session_id,
                    "approved": approved,
                    "timestamp": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                }
            )
            return approved
        except asyncio.TimeoutError:
            self.audit(
                {
                    "approval_id": approval_id,
                    "action": action,
                    "session_id": session_id,
                    "approved": False,
                    "reason": "timeout",
                }
            )
            return False

    def approve_request(
        self, approval_id: str, approved: bool, approver: str = "unknown"
    ) -> None:
        if approval_id in self.pending_approvals:
            self.audit(
                {
                    "approval_id": approval_id,
                    "approver": approver,
                    "decision": approved,
                    "timestamp": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                }
            )
            self.pending_approvals[approval_id].set_result(approved)
            del self.pending_approvals[approval_id]

    def audit(self, entry_data: dict) -> None:
        entry = AuditEntry(
            entry_id=self._generate_entry_id(entry_data),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            session_id=entry_data.get("session_id", "system"),
            action=entry_data.get("action", "unknown"),
            actor=entry_data.get("actor", "system"),
            params=entry_data.get("params", {}),
            result=entry_data.get("result", "pending"),
            risk_level=RiskLevel(entry_data.get("risk_level", "low")),
            approval_required=entry_data.get("requires_approval", False),
            approval_granted=entry_data.get("approved"),
        )

        self.audit_log.append(entry)

        if entry.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            asyncio.ensure_future(self._alert_monitoring(entry))

    def _generate_entry_id(self, entry: dict) -> str:
        content = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def _send_approval_notification(self, request: dict) -> None:
        if self.notification_service:
            await self.notification_service.send(
                {
                    "type": "approval_required",
                    "priority": "high",
                    "payload": request,
                }
            )

    async def _alert_monitoring(self, entry: AuditEntry) -> None:
        if self.notification_service:
            await self.notification_service.send(
                {
                    "type": "security_alert",
                    "severity": entry.risk_level.value,
                    "payload": {
                        "action": entry.action,
                        "actor": entry.actor,
                        "timestamp": entry.timestamp,
                    },
                }
            )

    def _sanitize_for_display(self, params: dict) -> dict:
        sanitized = {}
        for k, v in params.items():
            if isinstance(v, str) and len(v) > 500:
                sanitized[k] = v[:500] + "... [truncated]"
            else:
                sanitized[k] = v
        return sanitized

    # --- Constraint check implementations ---

    def _check_async_patterns(self, params: dict) -> dict:
        code = params.get("content", "")
        blocking = [
            "requests.get", "requests.post", "requests.put",
            "open(", "file(",
            "time.sleep(",
            "input(", "raw_input(",
        ]
        violations = [p for p in blocking if p in code]
        return {
            "passed": len(violations) == 0,
            "message": (
                f"Blocking I/O found: {violations}" if violations else "OK"
            ),
            "suggestion": "Use asyncio, aiohttp, or aiofiles",
        }

    def _check_type_hints(self, params: dict) -> dict:
        code = params.get("content", "")
        has_hints = "->" in code or "from typing import" in code
        return {
            "passed": has_hints,
            "message": "Type hints missing" if not has_hints else "OK",
            "suggestion": "Add type hints to all function signatures",
        }

    _SQL_DANGEROUS = [
        'f"SELECT', 'f"INSERT', 'f"UPDATE', 'f"DELETE',
        '+ "SELECT', '+ "INSERT', '+ "UPDATE',
    ]

    def _check_sql_safety(self, params: dict) -> dict:
        code = params.get("content", "")
        violations = [p for p in self._SQL_DANGEROUS if p in code]
        return {
            "passed": len(violations) == 0,
            "message": (
                f"SQL injection risk: {violations}" if violations else "OK"
            ),
            "suggestion": "Use SQLAlchemy ORM or parameterized queries",
        }

    _SECRET_PATTERNS = [
        r'password\s*=\s*["\'][^"\']+["\']',
        r'api_key\s*=\s*["\'][^"\']+["\']',
        r'secret\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']+["\']',
    ]

    def _check_secrets(self, params: dict) -> dict:
        code = params.get("content", "")
        violations = []
        for pattern in self._SECRET_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(pattern)
        return {
            "passed": len(violations) == 0,
            "message": (
                "Hardcoded secrets found" if violations else "OK"
            ),
            "suggestion": "Use environment variables or secret management",
        }

    def _check_circular_imports(self, params: dict) -> dict:
        imports_data = params.get("imports", params.get("ast_data", {}))
        if not imports_data:
            return {"passed": True, "message": "OK — no import data provided"}

        adjacency: dict = {}
        for mod, deps in imports_data.items():
            adjacency[mod] = set(deps)

        # DFS cycle detection
        visited: set = set()
        rec_stack: set = set()
        cycles: list = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        cycles.append((node, neighbor))
                        return True
                elif neighbor in rec_stack:
                    cycles.append((node, neighbor))
                    return True
            rec_stack.discard(node)
            return False

        for mod in list(adjacency.keys()):
            if mod not in visited:
                dfs(mod)

        if cycles:
            cycle_paths = [" → ".join(c) for c in cycles]
            return {
                "passed": False,
                "message": f"Circular imports detected: {cycle_paths}",
                "suggestion": "Extract shared dependencies into a separate module",
            }
        return {"passed": True, "message": "OK — no circular imports detected"}

    def _check_test_coverage(self, params: dict) -> dict:
        code = params.get("content", "")
        file_path = params.get("file_path", "")
        test_files = params.get("test_files", [])
        test_content = params.get("test_content", "")

        if not file_path and not test_files:
            return {"passed": True, "message": "OK — no test coverage data available"}

        is_test_file = (
            "test_" in file_path
            or file_path.endswith("_test.py")
            or "tests/" in file_path
            or "test_" in test_content
            or any("test_" in tf for tf in test_files)
        )

        has_assertions = any(
            kw in (code + test_content)
            for kw in ["assert", "def test_", "pytest", "unittest"]
        )

        if not is_test_file and not has_assertions:
            return {
                "passed": False,
                "message": "No test files found for new code",
                "suggestion": "Add unit tests with pytest to achieve >80% coverage",
            }
        return {"passed": True, "message": "OK — test file detected"}
