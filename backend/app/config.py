from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Harness Control Plane"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://harness:harness@localhost:5432/harness"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 50

    # Claude Code / MCP
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    MCP_SERVER_URL: str = "http://localhost:3001"

    # Harness
    MAX_ITERATIONS: int = 5
    MAX_COST_PER_TASK: float = 5.0
    TASK_TIMEOUT_SECONDS: int = 300
    RETRY_COUNT: int = 3

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Sandbox
    SANDBOX_NETWORK_MODE: str = "none"
    SANDBOX_CPU_LIMIT: str = "1"
    SANDBOX_MEMORY_LIMIT: str = "2g"
    SANDBOX_TIMEOUT_SECONDS: int = 300

    # Evaluation
    TEST_COVERAGE_THRESHOLD: int = 80
    SECURITY_SCAN_ENABLED: bool = True
    LINT_CHECK_ENABLED: bool = True

    # Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
