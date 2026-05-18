import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.app.harness.planner import TaskNode, TaskPlanner, TaskStatus

router = APIRouter()

# In-memory planner instance (replaced by DI in production)
_planner: Optional[TaskPlanner] = None


def get_planner() -> TaskPlanner:
    global _planner
    if _planner is None:
        _planner = TaskPlanner()
    return _planner


@router.post("/tasks")
async def create_task(request: dict):
    task_id = request.get("task_id") or f"task_{uuid.uuid4().hex[:12]}"
    description = request.get("description", "")
    task_type = request.get("task_type", "code")
    deps = request.get("dependencies", [])
    priority = request.get("priority", 5)
    timeout_seconds = request.get("timeout_seconds", 300)

    if not description:
        raise HTTPException(status_code=400, detail="Task description is required")

    planner = get_planner()

    try:
        node = TaskNode(
            id=task_id,
            description=description,
            task_type=task_type,
            deps=deps,
            timeout_seconds=timeout_seconds,
        )
        planner.add_task(node)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {
        "status": "queued",
        "task_id": task_id,
        "queue_position": len(planner.tasks),
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    planner = get_planner()

    if task_id not in planner.tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task = planner.tasks[task_id]
    return {
        "task_id": task.id,
        "status": task.status.value,
        "description": task.description,
        "type": task.task_type,
        "result": task.result,
        "error_log": task.error_log[-10:] if task.error_log else [],
        "retry_count": task.retry_count,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    planner = get_planner()
    tasks = list(planner.tasks.values())

    if status:
        tasks = [t for t in tasks if t.status.value == status]

    tasks = tasks[:limit]

    return {
        "tasks": [
            {
                "task_id": t.id,
                "status": t.status.value,
                "description": t.description,
                "type": t.task_type,
                "deps": t.deps,
            }
            for t in tasks
        ],
        "total": len(planner.tasks),
    }
