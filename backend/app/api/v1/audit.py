from typing import Optional
from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/audit")
async def query_audit_log(
    request: Request,
    session_id: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None, description="Cursor for pagination (entry_id of last item)"),
    limit: int = Query(100, ge=1, le=1000),
):
    return {
        "entries": [],
        "total": 0,
        "cursor": cursor,
        "next_cursor": None,
        "has_more": False,
        "filters": {
            "session_id": session_id,
            "start_time": start_time,
            "end_time": end_time,
        },
    }
