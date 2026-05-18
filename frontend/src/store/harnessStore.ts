import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { Task, ApprovalRequest, SystemMetrics, AuditEntry } from "../types/harness";

interface HarnessState {
  tasks: Task[];
  pendingApprovals: ApprovalRequest[];
  systemMetrics: SystemMetrics;
  auditLog: AuditEntry[];
  selectedTaskId: string | null;

  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  removeTask: (taskId: string) => void;
  addApproval: (approval: ApprovalRequest) => void;
  removeApproval: (approvalId: string) => void;
  updateMetrics: (metrics: Partial<SystemMetrics>) => void;
  addAuditEntry: (entry: AuditEntry) => void;
  setSelectedTask: (taskId: string | null) => void;
}

export const useHarnessStore = create<HarnessState>()(
  immer((set) => ({
    tasks: [],
    pendingApprovals: [],
    systemMetrics: {
      activeTasks: 0,
      queuedTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      avgExecutionTime: 0,
      systemLoad: 0,
      memoryUsage: 0,
    },
    auditLog: [],
    selectedTaskId: null,

    addTask: (task) =>
      set((state) => {
        state.tasks.unshift(task);
        state.systemMetrics.queuedTasks++;
      }),

    updateTask: (taskId, updates) =>
      set((state) => {
        const task = state.tasks.find((t) => t.id === taskId);
        if (task) {
          Object.assign(task, updates);
          if (updates.status === "running") {
            state.systemMetrics.queuedTasks = Math.max(0, state.systemMetrics.queuedTasks - 1);
            state.systemMetrics.activeTasks++;
          } else if (updates.status === "completed") {
            state.systemMetrics.activeTasks = Math.max(0, state.systemMetrics.activeTasks - 1);
            state.systemMetrics.completedTasks++;
          } else if (updates.status === "failed") {
            state.systemMetrics.activeTasks = Math.max(0, state.systemMetrics.activeTasks - 1);
            state.systemMetrics.failedTasks++;
          }
        }
      }),

    removeTask: (taskId) =>
      set((state) => {
        state.tasks = state.tasks.filter((t) => t.id !== taskId);
      }),

    addApproval: (approval) =>
      set((state) => {
        state.pendingApprovals.push(approval);
      }),

    removeApproval: (approvalId) =>
      set((state) => {
        state.pendingApprovals = state.pendingApprovals.filter(
          (a) => a.approvalId !== approvalId && a.id !== approvalId
        );
      }),

    updateMetrics: (metrics) =>
      set((state) => {
        Object.assign(state.systemMetrics, metrics);
      }),

    addAuditEntry: (entry) =>
      set((state) => {
        state.auditLog.unshift(entry);
        if (state.auditLog.length > 1000) {
          state.auditLog.pop();
        }
      }),

    setSelectedTask: (taskId) =>
      set((state) => {
        state.selectedTaskId = taskId;
      }),
  }))
);
