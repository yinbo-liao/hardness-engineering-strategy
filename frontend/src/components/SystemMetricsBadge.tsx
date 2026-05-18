import { Activity } from "lucide-react";
import type { SystemMetrics } from "../types/harness";

export function SystemMetricsBadge({ metrics }: { metrics: SystemMetrics }) {
  return (
    <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
      <span className="flex items-center gap-1" title="Active Tasks">
        <Activity className="w-3 h-3 text-blue-500" />
        {metrics.activeTasks}
      </span>
      <span title="Queued">{metrics.queuedTasks} queued</span>
      <span title="Completed" className="text-green-500">{metrics.completedTasks} done</span>
      {metrics.failedTasks > 0 && (
        <span title="Failed" className="text-red-500">{metrics.failedTasks} failed</span>
      )}
    </div>
  );
}
