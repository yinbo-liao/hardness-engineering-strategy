import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class PermissionLevel(Enum):
    READ = 1
    WRITE = 2
    EXECUTE = 3
    DEPLOY = 4
    ADMIN = 5


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str = ""
    required: bool = True


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    permission_required: PermissionLevel
    requires_approval: bool = False
    audit_level: str = "full"
    risk_level: str = "low"
    allowed_scopes: List[str] = Field(default_factory=lambda: ["*"])
    rate_limit: Optional[int] = None


@dataclass
class ToolExecutionContext:
    session_id: str
    user_permission: PermissionLevel
    task_scope: str
    sandbox_id: Optional[str] = None


@dataclass
class ToolExecutionResult:
    success: bool
    output: Optional[dict] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    execution_time_ms: int = 0
    audit_entry: Optional[dict] = None


class ToolRegistry:
    """
    Controlled tool system with schema validation, permission enforcement,
    rate limiting, and audit logging.

    8-step call pipeline:
    1. Tool existence check
    2. Scope validation
    3. Rate limiting
    4. Constraint check (Governance)
    5. Permission check
    6. Human-in-the-loop (if required)
    7. Audit logging
    8. Execute in sandbox
    """

    def __init__(self, governance=None):
        self.tools: Dict[str, ToolSchema] = {}
        self.implementations: Dict[str, Callable] = {}
        self.governance = governance
        self.audit_log: List[dict] = []
        self.rate_counters: Dict[str, List[float]] = {}

    def register(self, schema: ToolSchema, implementation: Callable) -> None:
        if schema.name in self.tools:
            raise ValueError(f"Tool '{schema.name}' is already registered")
        self.tools[schema.name] = schema
        self.implementations[schema.name] = implementation
        self.rate_counters[schema.name] = []

    def unregister(self, name: str) -> None:
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' is not registered")
        del self.tools[name]
        del self.implementations[name]
        self.rate_counters.pop(name, None)

    async def call(
        self,
        name: str,
        user_permission: PermissionLevel,
        params: Dict[str, Any],
        session_id: str,
        task_scope: str = "general",
    ) -> ToolExecutionResult:
        # 1. Tool existence check
        if name not in self.tools:
            return ToolExecutionResult(
                success=False, error=f"Unknown tool: {name}"
            )

        tool = self.tools[name]
        start_time = time.monotonic()

        # 2. Scope validation
        if task_scope not in tool.allowed_scopes and "*" not in tool.allowed_scopes:
            return ToolExecutionResult(
                success=False,
                error=f"Tool '{name}' not allowed for scope '{task_scope}'",
            )

        # 3. Rate limiting
        if tool.rate_limit:
            if not self._check_rate_limit(name, tool.rate_limit):
                return ToolExecutionResult(
                    success=False, error=f"Rate limit exceeded for tool '{name}'"
                )

        # 4. Constraint check (Governance)
        if self.governance:
            constraint_result = self.governance.check_constraint(
                name, params, task_scope
            )
            if not constraint_result["can_proceed"]:
                violations = constraint_result.get("violations", [])
                return ToolExecutionResult(
                    success=False,
                    error=f"Constraint violation: {violations}",
                )

        # 5. Permission check
        if user_permission.value < tool.permission_required.value:
            return ToolExecutionResult(
                success=False,
                error=(
                    f"Tool '{name}' requires {tool.permission_required.name} "
                    f"(you have {user_permission.name})"
                ),
            )

        # 6. Human-in-the-loop for high-risk operations
        if tool.requires_approval and self.governance:
            approved = await self.governance.request_human_approval(
                action=name,
                params=params,
                session_id=session_id,
                risk_level=tool.risk_level,
            )
            if not approved:
                return ToolExecutionResult(
                    success=False, error="Human approval denied"
                )

        # 7. Audit logging
        audit_entry = self._build_audit_entry(
            name=name,
            params=params,
            session_id=session_id,
            permission=user_permission,
            risk_level=tool.risk_level,
        )
        self.audit_log.append(audit_entry)
        if self.governance:
            self.governance.audit(audit_entry)

        # 8. Execute
        try:
            impl = self.implementations[name]
            result = await impl(**params)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return ToolExecutionResult(
                success=True,
                output=result if isinstance(result, dict) else {"value": result},
                logs=[],
                execution_time_ms=elapsed_ms,
                audit_entry=audit_entry,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return ToolExecutionResult(
                success=False,
                error=str(e),
                logs=[str(e)],
                execution_time_ms=elapsed_ms,
                audit_entry=audit_entry,
            )

    def _check_rate_limit(self, name: str, limit_per_minute: int) -> bool:
        now = time.monotonic()
        window = now - 60
        counters = self.rate_counters[name]
        counters[:] = [t for t in counters if t > window]
        if len(counters) >= limit_per_minute:
            return False
        counters.append(now)
        return True

    def _build_audit_entry(
        self,
        name: str,
        params: dict,
        session_id: str,
        permission: PermissionLevel,
        risk_level: str,
    ) -> dict:
        return {
            "tool": name,
            "params": self._sanitize_params(params),
            "session_id": session_id,
            "permission": permission.name,
            "risk_level": risk_level,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def _sanitize_params(self, params: dict) -> dict:
        sensitive = {"password", "token", "secret", "key", "api_key"}
        return {
            k: "***" if k.lower() in sensitive else v
            for k, v in params.items()
        }
