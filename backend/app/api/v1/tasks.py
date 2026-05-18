import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from backend.app.harness.planner import TaskNode, TaskStatus

router = APIRouter()


@router.post("/tasks")
async def create_task(request: Request):
    body = await request.json() if hasattr(request, "json") else request

    task_id = body.get("task_id") or f"task_{uuid.uuid4().hex[:12]}"
    description = body.get("description", "")
    task_type = body.get("task_type", "code")
    deps = body.get("dependencies", [])
    timeout_seconds = body.get("timeout_seconds", 300)

    if not description:
        raise HTTPException(status_code=400, detail="Task description is required")

    planner = request.app.state.planner

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

    # Trigger async execution via orchestrator
    orchestrator = request.app.state.orchestrator
    asyncio.create_task(_execute_task(node, orchestrator, request.app))

    return {
        "status": "queued",
        "task_id": task_id,
        "queue_position": len(planner.tasks),
    }


async def _execute_task(node: TaskNode, orchestrator, app):
    """Execute task in background and update state."""
    try:
        result = await orchestrator.execute_task(node)
        node.status = TaskStatus.COMPLETED
        node.result = result
    except Exception as e:
        node.status = TaskStatus.FAILED
        node.error_log.append(str(e))


@router.get("/tasks/{task_id}")
async def get_task_status(request: Request, task_id: str):
    planner = request.app.state.planner

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
    request: Request,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    planner = request.app.state.planner
    tasks = list(planner.tasks.values())

    if status:
        tasks = [t for t in tasks if t.status.value == status]

    tasks_sorted = sorted(tasks, key=lambda t: t.id, reverse=True)[:limit]

    return {
        "tasks": [
            {
                "task_id": t.id,
                "status": t.status.value,
                "description": t.description,
                "type": t.task_type,
                "deps": t.deps,
            }
            for t in tasks_sorted
        ],
        "total": len(planner.tasks),
    }
