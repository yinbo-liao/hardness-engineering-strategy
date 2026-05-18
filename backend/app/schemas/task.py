from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    task_id: Optional[str] = None
    description: str = Field(..., min_length=1, max_length=1024)
    task_type: str = Field(default="code", pattern=r"^(code|test|review|deploy|fix)$")
    dependencies: List[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)


class TaskResponse(BaseModel):
    status: str
    task_id: str
    queue_position: Optional[int] = None
    estimated_position: Optional[int] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    description: str
    type: str
    result: Optional[Dict[str, Any]] = None
    error_log: List[str] = Field(default_factory=list)
    retry_count: int = 3
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskListResponse(BaseModel):
    tasks: List[dict]
    total: int
