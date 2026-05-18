import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.app.harness.planner import TaskNode, TaskPlanner, TaskStatus
from backend.app.harness.context_manager import ContextManager
from backend.app.harness.tool_registry import (
    PermissionLevel,
    ToolExecutionResult,
    ToolRegistry,
)
from backend.app.harness.evaluator import Evaluator


class LoopPhase(Enum):
    REASONING = "reasoning"
    ACTION = "action"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    FEEDBACK = "feedback"


@dataclass
class SessionState:
    session_id: str
    task_id: str
    iterations: int = 0
    phase: LoopPhase = LoopPhase.REASONING
    history: List[dict] = field(default_factory=list)
    cost: float = 0.0
    started_at: float = field(default_factory=time.time)


class MaxIterationsExceeded(Exception):
    pass


class ClaudeCodeOrchestrator:
    """
    Orchestrates the full Agent Loop for Claude Code.

    Cycle: Context -> Reason -> Action -> Execute -> Evaluate -> Feedback
    Bounded to max_iterations (default 5) with cost tracking.
    Supports self-healing via reflect_and_fix on failure.
    """

    def __init__(
        self,
        planner: TaskPlanner,
        context_manager: ContextManager,
        tool_registry: ToolRegistry,
        evaluator: Evaluator,
        max_iterations: int = 5,
        max_cost_per_task: float = 5.0,
        websocket_manager=None,
    ):
        self.planner = planner
        self.context = context_manager
        self.tools = tool_registry
        self.evaluator = evaluator
        self.max_iterations = max_iterations
        self.max_cost_per_task = max_cost_per_task
        self.ws = websocket_manager
        self.active_sessions: Dict[str, SessionState] = {}

    async def execute_task(self, task: TaskNode) -> dict:
        session_id = f"session_{task.id}_{uuid.uuid4().hex[:8]}"
        session = SessionState(session_id=session_id, task_id=task.id)
        self.active_sessions[session_id] = session

        await self._emit("task_started", {"task_id": task.id, "session_id": session_id})

        task_context = self.context.build_context(task.description)

        for iteration in range(1, self.max_iterations + 1):
            session.iterations = iteration

            await self._emit(
                "iteration_started",
                {"task_id": task.id, "iteration": iteration},
            )

            # 1. REASON
            session.phase = LoopPhase.REASONING
            await self._emit(
                "phase_reasoning",
                {"task_id": task.id, "iteration": iteration},
            )
            reasoning = await self._claude_reason(session_id, task_context)

            # 2. ACTION
            session.phase = LoopPhase.ACTION
            actions = reasoning.get("actions", [])
            await self._emit(
                "phase_action",
                {"task_id": task.id, "actions": actions},
            )

            # 3. EXECUTE
            session.phase = LoopPhase.EXECUTION
            execution_results = await self._execute_actions(
                actions, session_id, task.task_type
            )
            await self._emit(
                "execution_completed",
                {"task_id": task.id, "results": len(execution_results)},
            )

            # 4. EVALUATE
            session.phase = LoopPhase.EVALUATION
            evaluation = await self.evaluator.evaluate(
                task=task,
                execution_results=execution_results,
                session_id=session_id,
            )
            await self._emit(
                "evaluation_completed",
                {
                    "task_id": task.id,
                    "passed": evaluation["passed"],
                    "score": evaluation["weighted_score"],
                },
            )

            session.history.append(
                {
                    "iteration": iteration,
                    "actions": actions,
                    "results": [
                        {"tool": r.get("action", {}).get("tool"), "status": r.get("status")}
                        for r in execution_results
                    ],
                    "evaluation": evaluation,
                    "cost": session.cost,
                }
            )

            # 5. FEEDBACK — if passed, return success
            if evaluation["passed"]:
                await self._emit(
                    "task_completed",
                    {
                        "task_id": task.id,
                        "iterations": iteration,
                        "score": evaluation["weighted_score"],
                    },
                )
                return {
                    "status": "success",
                    "iterations": iteration,
                    "results": execution_results,
                    "evaluation": evaluation,
                }

            session.phase = LoopPhase.FEEDBACK
            await self._emit(
                "phase_feedback",
                {"task_id": task.id, "feedback": evaluation.get("feedback")},
            )
            task_context = self._update_context_with_feedback(
                task_context, evaluation, execution_results
            )

        raise MaxIterationsExceeded(
            f"Task '{task.id}' exceeded max iterations ({self.max_iterations})"
        )

    async def reflect_and_fix(self, feedback: dict) -> dict:
        reflection_prompt = (
            "Analyze the following failure and generate a fix strategy:\n"
            f"{json.dumps(feedback, indent=2)}\n\n"
            "Provide: 1. Root cause analysis 2. Fix approach 3. Verification plan"
        )

        reflection = await self._call_claude(reflection_prompt)

        failed_id = feedback.get("failed_task", "unknown")
        fix_task = TaskNode(
            id=f"fix_{failed_id}_{uuid.uuid4().hex[:6]}",
            description=reflection.get("fix_approach", f"Auto-fix for {failed_id}"),
            task_type="fix",
        )
        self.planner.add_task(fix_task)
        return await self.execute_task(fix_task)

    async def _execute_actions(
        self, actions: list, session_id: str, task_type: str
    ) -> list:
        results = []
        for action in actions:
            tool_name = action.get("tool", "")
            params = action.get("params", {})
            try:
                result = await self.tools.call(
                    name=tool_name,
                    user_permission=PermissionLevel.WRITE,
                    params=params,
                    session_id=session_id,
                    task_scope=task_type,
                )
                results.append(
                    {
                        "action": action,
                        "status": "success" if result.success else "failed",
                        "output": result.output,
                        "error": result.error,
                        "execution_time_ms": result.execution_time_ms,
                    }
                )
            except Exception as e:
                results.append(
                    {"action": action, "status": "failed", "error": str(e)}
                )
        return results

    async def _claude_reason(self, session_id: str, context: dict) -> dict:
        return await self._call_claude(
            f"Given the following context, determine the next actions to take:\n"
            f"{json.dumps(context, indent=2)}\n\n"
            f"Respond with a JSON object containing an 'actions' array."
        )

    async def _call_claude(self, prompt: str) -> dict:
        # Stub — in production, this calls the Claude API via MCP
        return {"actions": [], "reasoning": "stub"}

    def _update_context_with_feedback(
        self, context: dict, evaluation: dict, results: list
    ) -> dict:
        context["feedback"] = {
            "evaluation": evaluation,
            "execution_results": results,
            "iteration": context.get("feedback", {}).get("iteration", 0) + 1,
        }
        return context

    async def _emit(self, event_type: str, payload: dict) -> None:
        if self.ws:
            await self.ws.broadcast(
                "main",
                {"type": event_type, "payload": payload, "timestamp": time.time()},
            )
