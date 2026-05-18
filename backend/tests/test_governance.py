import pytest
from backend.app.harness.governance import (
    Governance,
    RiskLevel,
    ConstraintViolation,
    SecurityViolation,
)


class TestRiskLevel:
    def test_enum_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.CRITICAL.value == "critical"


class TestGovernanceConstraints:
    @pytest.fixture
    def gov(self):
        return Governance()

    def test_forbidden_action_blocked(self, gov):
        result = gov.check_constraint("delete_prod_db", {}, "infra")
        assert result["can_proceed"] is False
        violations = [v for v in result["violations"] if v["rule"] == "forbidden_action"]
        assert len(violations) == 1

    def test_allowed_action_passes(self, gov):
        result = gov.check_constraint("read_file", {}, "code")
        assert result["can_proceed"] is True

    def test_async_pattern_check(self, gov):
        code_with_blocking = "import requests\nrequests.get('http://example.com')"
        result = gov._check_async_patterns({"content": code_with_blocking})
        assert result["passed"] is False
        assert "requests.get" in result["message"]

    def test_async_pattern_clean(self, gov):
        clean_code = "import aiohttp\nasync def fetch():\n    async with aiohttp.ClientSession() as s:\n        await s.get(url)"
        result = gov._check_async_patterns({"content": clean_code})
        assert result["passed"] is True

    def test_type_hint_check_missing(self, gov):
        code = "def foo(x, y):\n    return x + y"
        result = gov._check_type_hints({"content": code})
        assert result["passed"] is False

    def test_type_hint_check_present(self, gov):
        code = "from typing import List\ndef foo(x: int, y: int) -> int:\n    return x + y"
        result = gov._check_type_hints({"content": code})
        assert result["passed"] is True

    def test_sql_injection_check(self, gov):
        dangerous = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
        result = gov._check_sql_safety({"content": dangerous})
        assert result["passed"] is False

    def test_sql_safe(self, gov):
        safe = "from sqlalchemy import select\nstmt = select(User).where(User.id == user_id)"
        result = gov._check_sql_safety({"content": safe})
        assert result["passed"] is True

    def test_secret_check_hardcoded(self, gov):
        code = 'password = "super_secret_123"'
        result = gov._check_secrets({"content": code})
        assert result["passed"] is False

    def test_secret_check_clean(self, gov):
        code = 'password = os.environ.get("DB_PASSWORD")'
        result = gov._check_secrets({"content": code})
        assert result["passed"] is True


class TestGovernanceAudit:
    @pytest.fixture
    def gov(self):
        return Governance()

    def test_audit_entry_generated(self, gov):
        gov.audit({
            "session_id": "s1",
            "action": "write_file",
            "risk_level": "low",
            "actor": "test",
        })
        assert len(gov.audit_log) == 1
        entry = gov.audit_log[0]
        assert entry.action == "write_file"
        assert entry.session_id == "s1"
        assert len(entry.entry_id) == 16

    def test_high_risk_critical_triggers_alert(self, gov):
        gov.audit({
            "session_id": "s1",
            "action": "deploy_prod",
            "risk_level": "high",
        })
        assert len(gov.audit_log) == 1
        assert gov.audit_log[0].risk_level == RiskLevel.HIGH


class TestHumanApproval:
    @pytest.fixture
    def gov(self):
        return Governance(approval_timeout_seconds=1)

    @pytest.mark.asyncio
    async def test_approval_timeout_default_deny(self, gov):
        approved = await gov.request_human_approval(
            "deploy_prod", {"branch": "main"}, "session-1", "high"
        )
        assert approved is False

    def test_approve_request(self, gov):
        import asyncio
        async def _test():
            task = asyncio.ensure_future(
                gov.request_human_approval("deploy", {}, "s", "medium")
            )
            await asyncio.sleep(0.01)
            for aid in list(gov.pending_approvals.keys()):
                gov.approve_request(aid, True, approver="admin")
            result = await task
            assert result is True

        asyncio.get_event_loop().run_until_complete(_test())
