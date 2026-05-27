import { useState, useEffect, useCallback } from "react";
import {
  Shield,
  PlusCircle,
  List,
  History,
} from "lucide-react";
import { useWebSocket } from "../hooks/useWebSocket";
import { useHardnessStore } from "../store/hardnessStore";
import { TaskSubmissionForm } from "./TaskSubmissionForm";
import { TaskList } from "./TaskList";
import { ApprovalQueue } from "./ApprovalQueue";
import { AuditLogViewer } from "./AuditLogViewer";
import { AgentLoopVisualizer } from "./AgentLoopVisualizer";
import { EvaluationResults } from "./EvaluationResults";
import { CodeOutput } from "./CodeOutput";
import { ConnectionStatus } from "./ConnectionStatus";
import { SystemMetricsBadge } from "./SystemMetricsBadge";
import { UserMenu } from "./UserMenu";
import { FilterButton } from "./FilterButton";
import type { HardnessEvent, ApprovalRequest, SystemMetrics, Task } from "../types/hardness";

function getAuthToken(): string {
  return localStorage.getItem("Hardness_auth_token") || "";
}

export function HardnessDashboard() {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"tasks" | "approvals">("tasks");

  const {
    tasks,
    pendingApprovals,
    systemMetrics,
    addTask,
    updateTask,
    addApproval,
    removeApproval,
    updateMetrics,
  } = useHardnessStore();

  const wsUrl = `ws://127.0.0.1:8001/api/v1/Hardness/ws/main`;
  const { lastMessage, sendMessage, connectionStatus } = useWebSocket(wsUrl);

  useEffect(() => {
    if (!lastMessage) return;
    try {
      const event: HardnessEvent = JSON.parse(lastMessage.data);
      handleHardnessEvent(event);
    } catch {
      // Ignore malformed messages
    }
  }, [lastMessage]);

  const handleHardnessEvent = useCallback(
    (event: HardnessEvent) => {
      switch (event.type) {
        case "task_started":
        case "task_updated":
        case "task_completed":
        case "task_failed":
          updateTask(event.payload.task_id || "", event.payload as Partial<Task>);
          break;

        case "approval_required":
          addApproval(event.payload as unknown as ApprovalRequest);
          break;

        case "approval_resolved":
          removeApproval(event.payload.approval_id as string);
          break;

        case "iteration_started":
        case "phase_reasoning":
        case "phase_action":
        case "execution_completed":
        case "evaluation_completed":
        case "phase_feedback":
          updateTask(event.payload.task_id || "", {
            currentPhase: event.type,
            ...(event.payload as Partial<Task>),
          });
          break;

        case "system_metrics":
          updateMetrics(event.payload as Partial<SystemMetrics>);
          break;

        case "error":
          console.error("Hardness Error:", event.payload.message);
          break;
      }
    },
    [updateTask, addApproval, removeApproval, updateMetrics]
  );

  // Poll task list + selected task status every 2s
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/api/v1/Hardness/tasks");
        if (res.ok) {
          const data = await res.json();
          for (const t of data.tasks || []) {
            updateTask(t.task_id, {
              status: t.status,
              description: t.description,
              type: t.type,
            } as Partial<Task>);
          }
          updateMetrics({
            activeTasks: data.tasks.filter((t: any) => t.status === "running").length,
            queuedTasks: data.tasks.filter((t: any) => t.status === "pending").length,
            completedTasks: data.tasks.filter((t: any) => t.status === "completed").length,
          });
        }
        if (selectedTask) {
          const detail = await fetch(`/api/v1/Hardness/tasks/${selectedTask}`);
          if (detail.ok) {
            const d = await detail.json();
            const r = (d.result && typeof d.result === "object") ? d.result : {};
            const ev = (r && typeof r === "object") ? (r.evaluation || {}) : {};
            updateTask(selectedTask, {
              status: d.status,
              description: d.description,
              type: d.type,
              result: d.result,
              errorLog: d.error_log || [],
              currentIteration: (typeof r.iterations === "number") ? r.iterations : 0,
              maxIterations: 5,
              currentPhase: d.status === "completed" ? "task_completed"
                : d.status === "running" ? (r.iterations === 0 ? "phase_reasoning" : "phase_action")
                : undefined,
              progress: ev.weighted_score ? Math.round(ev.weighted_score * 100) : d.status === "completed" ? 100 : 20,
            } as Partial<Task>);
          }
        }
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [updateTask, updateMetrics, selectedTask]);

  const handleSubmitTask = async (description: string, taskType: string) => {
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

    try {
      const response = await fetch(
        "/api/v1/Hardness/tasks",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify({
            task_id: taskId,
            description,
            task_type: taskType,
            dependencies: [],
            priority: 5,
            timeout_seconds: 300,
          }),
        }
      );

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const newTask: Task = {
        id: taskId,
        description,
        type: taskType as Task["type"],
        status: "queued",
        progress: 0,
        currentIteration: 0,
        maxIterations: 5,
        createdAt: new Date().toISOString(),
        logs: [],
      };

      addTask(newTask);
    } catch (error) {
      console.error("Failed to queue task:", error);
    }
  };

  const handleApproval = async (approvalId: string, approved: boolean, comment?: string) => {
    sendMessage(
      JSON.stringify({
        type: "approval_response",
        approval_id: approvalId,
        approved,
        comment,
        approver: "operator",
        timestamp: new Date().toISOString(),
      })
    );
    removeApproval(approvalId);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Shield className="w-8 h-8 text-blue-600" />
              Hardness Control Center
            </h1>
            <ConnectionStatus status={connectionStatus} />
          </div>
          <div className="flex items-center space-x-4">
            <SystemMetricsBadge metrics={systemMetrics} />
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <PlusCircle className="w-5 h-5" />
                New Task
              </h2>
              <TaskSubmissionForm onSubmit={handleSubmitTask} />
            </section>

            <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <List className="w-5 h-5" />
                  Active Tasks
                  <span className="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 rounded-full">
                    {tasks.filter((t) => t.status === "running").length} running
                  </span>
                </h2>
                <div className="flex space-x-2">
                  <FilterButton
                    active={activeTab === "tasks"}
                    onClick={() => setActiveTab("tasks")}
                    label="All Tasks"
                    count={tasks.length}
                  />
                  <FilterButton
                    active={activeTab === "approvals"}
                    onClick={() => setActiveTab("approvals")}
                    label="Approvals"
                    count={pendingApprovals.length}
                    badgeColor="amber"
                  />
                </div>
              </div>

              {activeTab === "tasks" ? (
                <TaskList tasks={tasks} selectedTask={selectedTask} onSelectTask={setSelectedTask} />
              ) : (
                <ApprovalQueue approvals={pendingApprovals} onApprove={handleApproval} />
              )}
            </section>
          </div>

          <div className="space-y-6">
            <AgentLoopVisualizer
              taskId={selectedTask}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
            />

            <CodeOutput
              taskId={selectedTask}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
            />

            <EvaluationResults
              taskId={selectedTask}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
            />

            <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <History className="w-5 h-5" />
                Audit Trail
              </h2>
              <AuditLogViewer maxEntries={50} />
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
