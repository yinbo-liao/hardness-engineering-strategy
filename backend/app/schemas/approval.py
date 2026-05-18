from typing import List, Optional

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    approval_id: str
    session_id: str
    action: str
    risk_level: str
    requested_at: str


class ApprovalListResponse(BaseModel):
    pending: List[ApprovalRequest]


class ApprovalAction(BaseModel):
    approver: Optional[str] = "system"
    comment: Optional[str] = None


class ApprovalResponse(BaseModel):
    status: str
    approval_id: str
