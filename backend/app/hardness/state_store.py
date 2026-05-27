import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.checkpoint import Checkpoint
from backend.app.models.event import HardnessEvent


class StateStore:
    """
    PostgreSQL-backed state persistence with event sourcing.

    Provides:
    - Atomic checkpoint saves with integrity verification
    - Event sourcing for complete audit and replay
    - Resume-from-checkpoint on restart
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Checkpoint operations ---

    async def save_checkpoint(
        self,
        task_id: str,
        state: dict,
        task_status: str,
        error_log: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> Checkpoint:
        content = json.dumps(state, indent=2, sort_keys=True)
        state_hash = hashlib.sha256(content.encode()).hexdigest()

        checkpoint = Checkpoint(
            task_id=task_id,
            state=state,
            state_hash=state_hash,
            task_status=task_status,
            error_log=error_log or [],
            checkpoint_metadata=metadata or {},
        )
        self.session.add(checkpoint)
        await self.session.flush()
        return checkpoint

    async def load_latest_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        result = await self.session.execute(
            select(Checkpoint)
            .where(Checkpoint.task_id == task_id)
            .order_by(Checkpoint.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def verify_checkpoint_integrity(self, checkpoint_id: str) -> bool:
        cp = await self.session.get(Checkpoint, checkpoint_id)
        if cp is None:
            return False
        content = json.dumps(cp.state, indent=2, sort_keys=True)
        computed = hashlib.sha256(content.encode()).hexdigest()
        return computed == cp.state_hash

    # --- Event sourcing ---

    async def append_event(
        self, task_id: str, event_type: str, data: dict
    ) -> HardnessEvent:
        max_seq_result = await self.session.execute(
            text(
                "SELECT COALESCE(MAX(sequence), -1) FROM \"Hardness_events\" "
                "WHERE task_id = :tid"
            ),
            {"tid": task_id},
        )
        next_seq = max_seq_result.scalar() + 1

        event = HardnessEvent(
            task_id=task_id,
            type=event_type,
            data=data,
            sequence=next_seq,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_event_stream(
        self,
        task_id: str,
        from_sequence: int = 0,
        limit: int = 100,
    ) -> List[HardnessEvent]:
        result = await self.session.execute(
            select(HardnessEvent)
            .where(
                HardnessEvent.task_id == task_id,
                HardnessEvent.sequence >= from_sequence,
            )
            .order_by(HardnessEvent.sequence)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def replay_events(self, task_id: str) -> List[dict]:
        events = await self.get_event_stream(task_id, from_sequence=0, limit=10000)
        return [
            {
                "sequence": e.sequence,
                "type": e.type,
                "data": e.data,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]
