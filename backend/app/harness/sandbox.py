import asyncio
import os
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SandboxStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SandboxConfig:
    image: str = "harness-sandbox:latest"
    cpu_limit: str = "1"
    memory_limit: str = "2g"
    disk_limit_mb: int = 1024
    network_mode: str = "none"
    read_only_root: bool = True
    timeout_seconds: int = 300
    workspace_path: str = "/workspace"
    tmpfs_size: str = "500m"


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: int
    status: SandboxStatus
    artifacts: Dict[str, str] = field(default_factory=dict)


class SandboxManager:
    """
    Manages isolated Docker sandbox containers for code execution.

    Security posture:
    - network_mode=none — no network access
    - read_only rootfs — only /workspace and /tmp writable
    - non-root user (UID 1000)
    - seccomp profile restricts dangerous syscalls
    - resource limits (CPU, memory, disk)
    - timeout enforcement
    """

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
        docker_socket: str = "/var/run/docker.sock",
    ):
        self.config = config or SandboxConfig()
        self.docker_socket = docker_socket
        self.active_containers: Dict[str, dict] = {}
        self._workspace_base = tempfile.gettempdir()

    async def create_container(self, task_id: str) -> str:
        container_name = f"harness-sandbox-{task_id}"
        workspace = os.path.join(self._workspace_base, f"harness-{task_id}")
        os.makedirs(workspace, exist_ok=True)

        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            f"--network={self.config.network_mode}",
            f"--cpus={self.config.cpu_limit}",
            f"--memory={self.config.memory_limit}",
            f"--storage-opt", f"size={self.config.disk_limit_mb}m",
            "--read-only" if self.config.read_only_root else "",
            f"--tmpfs", f"/tmp:noexec,nosuid,size={self.config.tmpfs_size},uid=1000,gid=1000",
            "--security-opt", "no-new-privileges:true",
            "--security-opt", "seccomp=./docker/seccomp-profile.json",
            "--cap-drop", "ALL",
            "--cap-add", "CHOWN",
            "--cap-add", "SETGID",
            "--cap-add", "SETUID",
            "--user", "1000:1000",
            "-v", f"{workspace}:/workspace",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-e", "PYTHONUNBUFFERED=1",
            self.config.image,
            "sleep", "infinity",
        ]

        cmd = [c for c in cmd if c]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(
                f"Failed to create sandbox container: {stderr.decode()}"
            )

        container_id = stdout.decode().strip()
        self.active_containers[task_id] = {
            "id": container_id,
            "name": container_name,
            "workspace": workspace,
            "created_at": time.time(),
        }
        return container_id

    async def execute(
        self, task_id: str, command: List[str], env: Optional[dict] = None
    ) -> SandboxResult:
        if task_id not in self.active_containers:
            raise ValueError(f"No active sandbox for task '{task_id}'")

        container = self.active_containers[task_id]
        cmd = ["docker", "exec"]

        if env:
            for k, v in env.items():
                cmd.extend(["-e", f"{k}={v}"])

        cmd.append(container["name"])
        cmd.extend(command)

        start = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds,
            )
            elapsed = int((time.monotonic() - start) * 1000)

            return SandboxResult(
                exit_code=process.returncode or 0,
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                execution_time_ms=elapsed,
                status=(
                    SandboxStatus.COMPLETED
                    if process.returncode == 0
                    else SandboxStatus.FAILED
                ),
            )
        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - start) * 1000)
            await self.kill_container(task_id)
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {self.config.timeout_seconds}s",
                execution_time_ms=elapsed,
                status=SandboxStatus.TIMEOUT,
            )

    async def kill_container(self, task_id: str) -> None:
        if task_id not in self.active_containers:
            return

        container = self.active_containers.pop(task_id)
        process = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container["name"],
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

    async def cleanup(self) -> None:
        for task_id in list(self.active_containers.keys()):
            await self.kill_container(task_id)

    async def get_container_status(self, task_id: str) -> Optional[dict]:
        if task_id not in self.active_containers:
            return None

        container = self.active_containers[task_id]
        process = await asyncio.create_subprocess_exec(
            "docker", "inspect", container["name"],
            "--format", "{{.State.Status}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        status = stdout.decode().strip()

        return {
            "task_id": task_id,
            "container_name": container["name"],
            "status": status,
            "created_at": container["created_at"],
            "uptime_seconds": time.time() - container["created_at"],
        }
