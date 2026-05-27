import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func

from backend.app.db.session import async_session_factory
from backend.app.hardness.planner import TaskNode, TaskStatus
from backend.app.hardness.state_store import StateStore
from backend.app.models.task import Task as TaskModel, TaskStatus as DBTaskStatus
from backend.app.schemas.task import TaskRequest

router = APIRouter()


async def get_state_store(request: Request) -> StateStore:
    """Per-request StateStore dependency."""
    async with async_session_factory() as session:
        store = StateStore(session)
        yield store
        await session.commit()


@router.post("/tasks")
async def create_task(
    request: Request,
    task_input: TaskRequest,
    state_store: StateStore = Depends(get_state_store),
):
    task_id = task_input.task_id or f"task_{uuid.uuid4().hex[:12]}"
    description = task_input.description
    task_type = task_input.task_type
    deps = task_input.dependencies
    timeout_seconds = task_input.timeout_seconds

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

    # Persist to database
    db_task = TaskModel(
        id=task_id,
        description=description,
        task_type=task_type,
        status="pending",
        deps=deps,
        timeout_seconds=timeout_seconds,
    )
    state_store.session.add(db_task)
    await state_store.session.flush()

    # Save initial checkpoint
    await state_store.save_checkpoint(
        task_id=task_id,
        state=node.to_dict(),
        task_status="pending",
    )

    # Trigger async execution via orchestrator
    orchestrator = request.app.state.orchestrator
    asyncio.create_task(_execute_task(node, orchestrator, request.app))

    return {
        "status": "queued",
        "task_id": task_id,
        "queue_position": len(planner.tasks),
    }


async def _execute_task(node: TaskNode, orchestrator, app):
    """Execute task in background and persist state changes."""
    try:
        async with async_session_factory() as session:
            state_store = StateStore(session)

            result = await orchestrator.execute_task(node)
            node.status = TaskStatus.COMPLETED
            node.result = result

            # Update DB
            db_task = await session.get(TaskModel, node.id)
            if db_task:
                db_task.status = "completed"
                db_task.result = result

            await state_store.save_checkpoint(
                task_id=node.id,
                state=node.to_dict(),
                task_status="completed",
            )
            await state_store.append_event(
                task_id=node.id,
                event_type="task_completed",
                data={"result": result},
            )
            await session.commit()

    except Exception as e:
        node.status = TaskStatus.FAILED
        node.error_log.append(str(e))

        try:
            async with async_session_factory() as session:
                state_store = StateStore(session)
                db_task = await session.get(TaskModel, node.id)
                if db_task:
                    db_task.status = "failed"
                    db_task.error_log = node.error_log
                await state_store.save_checkpoint(
                    task_id=node.id,
                    state=node.to_dict(),
                    task_status="failed",
                    error_log=node.error_log,
                )
                await state_store.append_event(
                    task_id=node.id,
                    event_type="task_failed",
                    data={"error": str(e)},
                )
                await session.commit()
        except Exception:
            pass  # Best-effort persistence on failure


@router.get("/tasks/{task_id}")
async def get_task_status(request: Request, task_id: str):
    planner = request.app.state.planner

    # Check in-memory planner first (has live execution state)
    if task_id in planner.tasks:
        task = planner.tasks[task_id]
        return {
            "task_id": task.id,
            "status": task.status.value,
            "description": task.description,
            "type": task.task_type,
            "result": task.result,
            "error_log": task.error_log[-10:] if task.error_log else [],
            "retry_count": task.retry_count,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "memory",
        }

    # Fall back to database
    async with async_session_factory() as session:
        db_task = await session.get(TaskModel, task_id)
        if db_task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return {
            "task_id": db_task.id,
            "status": db_task.status.value if hasattr(db_task.status, 'value') else db_task.status,
            "description": db_task.description,
            "type": db_task.task_type,
            "result": db_task.result,
            "error_log": (db_task.error_log or [])[-10:],
            "retry_count": db_task.retry_count,
            "created_at": db_task.created_at.isoformat() if db_task.created_at else None,
            "updated_at": db_task.updated_at.isoformat() if db_task.updated_at else None,
            "source": "database",
        }


@router.get("/tasks")
async def list_tasks(
    request: Request,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    # Merge in-memory and DB tasks
    planner = request.app.state.planner
    in_memory = {t.id: t for t in planner.tasks.values()}

    async with async_session_factory() as session:
        query = select(TaskModel).order_by(TaskModel.created_at.desc()).limit(limit)
        if status:
            try:
                db_status = DBTaskStatus(status)
                query = query.where(TaskModel.status == db_status)
            except ValueError:
                pass

        result = await session.execute(query)
        db_tasks = result.scalars().all()

        tasks_output = []
        seen = set()

        # In-memory tasks first (latest state)
        for tid, t in in_memory.items():
            if status and t.status.value != status:
                continue
            seen.add(tid)
            tasks_output.append({
                "task_id": t.id,
                "status": t.status.value,
                "description": t.description,
                "type": t.task_type,
                "deps": t.deps,
                "source": "memory",
            })

        # DB tasks not already in memory
        for db_task in db_tasks:
            if db_task.id in seen:
                continue
            tasks_output.append({
                "task_id": db_task.id,
                "status": db_task.status.value if hasattr(db_task.status, 'value') else db_task.status,
                "description": db_task.description,
                "type": db_task.task_type,
                "deps": db_task.deps,
                "source": "database",
            })

        # Apply limit after merge
        tasks_output = tasks_output[:limit]

        # Count total
        count_query = select(func.count(TaskModel.id))
        count_result = await session.execute(count_query)
        db_total = count_result.scalar() or 0
        total = max(len(in_memory), db_total)

        return {
            "tasks": tasks_output,
            "total": total,
        }
