import os
import tempfile

import pytest
from backend.app.harness.security_audit import SecurityAuditor, Severity, SecurityFinding, AuditReport


class TestSecurityFinding:
    def test_defaults(self):
        f = SecurityFinding(
            id="TEST-001",
            category="secret_detection",
            severity=Severity.CRITICAL,
            description="Test finding",
        )
        assert f.severity == Severity.CRITICAL
        assert f.location == ""


class TestAuditReport:
    def test_counts(self):
        report = AuditReport(
            findings=[
                SecurityFinding(id="1", category="c", severity=Severity.CRITICAL, description="c1"),
                SecurityFinding(id="2", category="c", severity=Severity.CRITICAL, description="c2"),
                SecurityFinding(id="3", category="c", severity=Severity.HIGH, description="h1"),
                SecurityFinding(id="4", category="c", severity=Severity.MEDIUM, description="m1"),
            ]
        )
        assert report.critical_count == 2
        assert report.high_count == 1
        assert report.passed is False

    def test_passed_when_no_critical_or_high(self):
        report = AuditReport(
            findings=[
                SecurityFinding(id="1", category="c", severity=Severity.LOW, description="low"),
                SecurityFinding(id="2", category="c", severity=Severity.MEDIUM, description="med"),
            ]
        )
        assert report.passed is True


class TestSecurityAuditor:
    @pytest.fixture
    def auditor(self):
        return SecurityAuditor(root_path=".")

    @pytest.mark.asyncio
    async def test_run_all_returns_report(self, auditor):
        report = await auditor.run_all()
        assert isinstance(report, AuditReport)
        assert "total" in report.summary
        assert "critical" in report.summary

    @pytest.mark.asyncio
    async def test_scan_secrets_in_clean_file(self, auditor):
        with tempfile.TemporaryDirectory() as tmp:
            clean_file = os.path.join(tmp, "clean.py")
            with open(clean_file, "w") as f:
                f.write("import os\npassword = os.environ.get('PASS')\n")

            auditor.root_path = tmp
            findings = await auditor.scan_secrets()
            assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_scan_secrets_detects_hardcoded(self, auditor):
        with tempfile.TemporaryDirectory() as tmp:
            secret_file = os.path.join(tmp, "config.py")
            with open(secret_file, "w") as f:
                f.write('password = "super_secret_value_12345"\n')
                f.write('api_key = "sk-ant-api-key-with-20chars"\n')

            auditor.root_path = tmp
            findings = await auditor.scan_secrets()
            assert len(findings) >= 2

    def test_check_container_config_valid(self, auditor):
        auditor.root_path = os.path.join(os.path.dirname(__file__), "..", "..")
        findings = auditor.check_container_config()
        for f in findings:
            assert f.category == "container_hardening"

    def test_check_network_config(self, auditor):
        auditor.root_path = os.path.join(os.path.dirname(__file__), "..", "..")
        findings = auditor.check_network_config()
        for f in findings:
            assert f.category == "network_exposure"

    def test_exclude_dirs_respected(self, auditor):
        excluded = auditor._EXCLUDE_FILES
        assert ".git" in excluded
        assert "node_modules" in excluded
        assert "__pycache__" in excluded

    def test_secret_patterns_defined(self, auditor):
        assert len(auditor._SECRET_PATTERNS) == 5
