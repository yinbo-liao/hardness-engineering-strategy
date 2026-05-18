import { Clock, RotateCw } from "lucide-react";
import type { Task } from "../types/harness";
import { statusColor, formatDate, truncate } from "../utils/formatters";

interface TaskCardProps {
  task: Task;
  selected: boolean;
  onSelect: (id: string) => void;
}

export function TaskCard({ task, selected, onSelect }: TaskCardProps) {
  return (
    <button
      onClick={() => onSelect(task.id)}
      className={`w-full text-left p-4 rounded-lg border transition-colors ${
        selected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
          : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 dark:text-white truncate">
            {truncate(task.description, 60)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{task.id}</p>
        </div>
        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(task.status)}`}>
          {task.status}
        </span>
      </div>

      {task.status === "running" && (
        <div className="mt-3 space-y-1.5">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <RotateCw className="w-3 h-3 animate-spin" />
            Iteration {task.currentIteration}/{task.maxIterations}
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all"
              style={{ width: `${Math.min(100, (task.currentIteration / task.maxIterations) * 100)}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex items-center gap-1 mt-2 text-xs text-gray-400">
        <Clock className="w-3 h-3" />
        {formatDate(task.createdAt)}
      </div>
    </button>
  );
}
