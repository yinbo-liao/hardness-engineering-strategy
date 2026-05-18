from fastapi import APIRouter, HTTPException, Request, status

from backend.app.harness.errors import not_found

router = APIRouter()

_pending_approvals: dict = {}


@router.get("/approvals")
async def list_pending_approvals():
    return {
        "pending": [
            {
                "approval_id": aid,
                "action": data.get("action"),
                "risk_level": data.get("risk_level"),
                "requested_at": data.get("requested_at"),
            }
            for aid, data in _pending_approvals.items()
        ]
    }


@router.post("/approvals/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    body: dict = None,
    request: Request = None,
):
    if approval_id not in _pending_approvals:
        return not_found(request, "Approval", approval_id)

    comment = (body or {}).get("comment")
    approver = (body or {}).get("approver", "system")

    result = _pending_approvals.pop(approval_id)
    result["status"] = "approved"
    result["comment"] = comment
    result["approver"] = approver

    app = request.app if request else None
    if app and hasattr(app.state, "governance"):
        governance = app.state.governance
        governance.approve_request(approval_id, True, approver=approver)

    return {"status": "approved", "approval_id": approval_id}


@router.post("/approvals/{approval_id}/deny")
async def deny_request(
    approval_id: str,
    body: dict = None,
    request: Request = None,
):
    if approval_id not in _pending_approvals:
        return not_found(request, "Approval", approval_id)

    comment = (body or {}).get("comment")
    approver = (body or {}).get("approver", "system")

    result = _pending_approvals.pop(approval_id)
    result["status"] = "denied"
    result["comment"] = comment
    result["approver"] = approver

    app = request.app if request else None
    if app and hasattr(app.state, "governance"):
        governance = app.state.governance
        governance.approve_request(approval_id, False, approver=approver)

    return {"status": "denied", "approval_id": approval_id}
