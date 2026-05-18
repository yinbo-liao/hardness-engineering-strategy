import { useHarnessStore } from "../store/harnessStore";

export function useTasks() {
  return useHarnessStore((s) => s.tasks);
}

export function useTask(taskId: string | null) {
  return useHarnessStore((s) => s.tasks.find((t) => t.id === taskId) ?? null);
}

export function usePendingApprovals() {
  return useHarnessStore((s) => s.pendingApprovals);
}

export function useSystemMetrics() {
  return useHarnessStore((s) => s.systemMetrics);
}

export function useSelectedTaskId() {
  return useHarnessStore((s) => s.selectedTaskId);
}

export function useAuditLog() {
  return useHarnessStore((s) => s.auditLog);
}
