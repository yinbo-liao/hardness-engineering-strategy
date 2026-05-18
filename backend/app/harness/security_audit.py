"""
Security audit scanner for the Harness Control Plane.

Checks:
- Dependency vulnerabilities (safety check)
- Container security posture
- Secret leakage in codebase
- Network exposure surface
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityFinding:
    id: str
    category: str
    severity: Severity
    description: str
    location: str = ""
    remediation: str = ""
    cve: Optional[str] = None


@dataclass
class AuditReport:
    findings: List[SecurityFinding] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.summary:
            critical = sum(1 for f in self.findings if f.severity == Severity.CRITICAL)
            high = sum(1 for f in self.findings if f.severity == Severity.HIGH)
            self.summary = {
                "total": len(self.findings),
                "critical": critical,
                "high": high,
                "medium": sum(1 for f in self.findings if f.severity == Severity.MEDIUM),
                "low": sum(1 for f in self.findings if f.severity == Severity.LOW),
            }

    @property
    def passed(self) -> bool:
        return self.summary.get("critical", 0) == 0 and self.summary.get("high", 0) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)


class SecurityAuditor:
    """
    Runs security checks on the harness deployment.

    Categories:
    - dependency_scan — vulnerable packages
    - secret_detection — hardcoded credentials
    - container_hardening — Docker security posture
    - network_exposure — open ports, exposed services
    """

    _SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\'][\w\-]{20,}["\']', "API key"),
        (r'(?i)(password|passwd)\s*[:=]\s*["\'][^"\']{4,}["\']', "Password"),
        (r'(?i)(secret)\s*[:=]\s*["\'][^"\']{8,}["\']', "Secret"),
        (r'(?i)(token)\s*[:=]\s*["\'][\w\-.]{20,}["\']', "Token"),
        (r'(?i)-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----', "Private key"),
    ]

    _EXCLUDE_FILES = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

    def __init__(self, root_path: str = "."):
        self.root_path = root_path

    async def run_all(self) -> AuditReport:
        findings: list = []
        findings.extend(await self.scan_secrets())
        findings.extend(self.check_dependencies())
        findings.extend(self.check_container_config())
        findings.extend(self.check_network_config())

        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)

        return AuditReport(findings=findings)

    async def scan_secrets(self) -> List[SecurityFinding]:
        findings: list = []

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            dirnames[:] = [d for d in dirnames if d not in self._EXCLUDE_FILES]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, encoding="utf-8", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            for pattern, secret_type in self._SECRET_PATTERNS:
                                if re.search(pattern, line):
                                    findings.append(
                                        SecurityFinding(
                                            id=f"SECRET-{len(findings)+1:03d}",
                                            category="secret_detection",
                                            severity=Severity.CRITICAL,
                                            description=f"Potential {secret_type} found",
                                            location=f"{filepath}:{lineno}",
                                            remediation=f"Remove hardcoded {secret_type.lower()} and use environment variables",
                                        )
                                    )
                except (OSError, UnicodeDecodeError):
                    pass

        return findings

    def check_dependencies(self) -> List[SecurityFinding]:
        findings: list = []
        req_path = os.path.join(
            self.root_path, "backend", "requirements.txt"
        )

        if not os.path.exists(req_path):
            return findings

        try:
            result = subprocess.run(
                ["python", "-m", "safety", "check", "--file", req_path, "--output", "json"],
                capture_output=True, text=True, timeout=30,
                cwd=self.root_path,
            )
            if result.returncode != 0 and result.stdout:
                data = json.loads(result.stdout)
                for vuln in data.get("vulnerabilities", []):
                    findings.append(
                        SecurityFinding(
                            id=f"DEP-{len(findings)+1:03d}",
                            category="dependency_scan",
                            severity=Severity(vuln.get("severity", "medium").lower()),
                            description=f"{vuln['package_name']} {vuln.get('vulnerable_spec', '')}: {vuln.get('advisory', '')}",
                            cve=vuln.get("cve"),
                            remediation=f"Upgrade to {vuln.get('fixed_version', 'latest')}",
                        )
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

        return findings

    def check_container_config(self) -> List[SecurityFinding]:
        findings: list = []
        compose_path = os.path.join(self.root_path, "docker-compose.harness.yml")

        if not os.path.exists(compose_path):
            return findings

        try:
            with open(compose_path) as f:
                content = f.read()
        except OSError:
            return findings

        checks = [
            ("network_mode: none", Severity.CRITICAL, "Sandbox should use network_mode: none"),
            ("read_only: true", Severity.HIGH, "Sandbox should use read-only root filesystem"),
            ("no-new-privileges:true", Severity.HIGH, "Sandbox should prevent privilege escalation"),
            ("cap_drop:\n      - ALL", Severity.HIGH, "All capabilities should be dropped"),
            ("user: \"1000:1000\"", Severity.MEDIUM, "Sandbox should run as non-root user"),
        ]

        for check, severity, description in checks:
            if check not in content:
                findings.append(
                    SecurityFinding(
                        id=f"CONTAINER-{len(findings)+1:03d}",
                        category="container_hardening",
                        severity=severity,
                        description=description,
                        remediation=check,
                    )
                )

        return findings

    def check_network_config(self) -> List[SecurityFinding]:
        findings: list = []
        compose_path = os.path.join(self.root_path, "docker-compose.harness.yml")

        if not os.path.exists(compose_path):
            return findings

        try:
            with open(compose_path) as f:
                content = f.read()
        except OSError:
            return findings

        if "harness-internal:\n    driver: bridge\n    internal: true" not in content:
            findings.append(
                SecurityFinding(
                    id="NET-001",
                    category="network_exposure",
                    severity=Severity.HIGH,
                    description="Internal network should be isolated (internal: true)",
                    remediation="Set internal: true on harness-internal bridge network",
                )
            )

        return findings
