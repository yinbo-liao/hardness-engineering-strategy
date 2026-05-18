from typing import List, Optional

from pydantic import BaseModel, Field


class AuditEntrySchema(BaseModel):
    entry_id: str
    timestamp: str
    session_id: str
    action: str
    actor: str
    result: str
    risk_level: str


class AuditLogResponse(BaseModel):
    entries: List[AuditEntrySchema]
    total: int
    page: int = 1


class AuditQueryParams(BaseModel):
    session_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
