import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.task_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "main"):
        await websocket.accept()
        if channel not in self.connections:
            self.connections[channel] = set()
        self.connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "main"):
        if channel in self.connections:
            self.connections[channel].discard(websocket)
        for subs in self.task_subscriptions.values():
            subs.discard(websocket)

    async def broadcast(self, channel: str, message: dict):
        if channel not in self.connections:
            return
        payload = json.dumps(message)
        dead: set = set()
        for ws in self.connections[channel]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        self.connections[channel] -= dead

    async def broadcast_task_event(self, task_id: str, event: dict):
        payload = json.dumps(event)
        subs = self.task_subscriptions.get(task_id, set())
        dead: set = set()
        for ws in subs:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        if dead:
            self.task_subscriptions[task_id] = subs - dead


manager = WebSocketManager()


@router.websocket("/ws/main")
async def main_websocket(websocket: WebSocket):
    await manager.connect(websocket, "main")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "approval_response":
                await manager.broadcast(
                    "main",
                    {
                        "type": "approval_resolved",
                        "payload": {
                            "approval_id": message.get("approval_id"),
                            "approved": message.get("approved"),
                            "approver": message.get("approver"),
                        },
                    },
                )
            elif msg_type == "subscribe_task":
                task_id = message.get("task_id")
                if task_id not in manager.task_subscriptions:
                    manager.task_subscriptions[task_id] = set()
                manager.task_subscriptions[task_id].add(websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "main")
    except Exception:
        manager.disconnect(websocket, "main")
