import { FileCode, Layers } from "lucide-react";
import { useTask } from "../hooks/useHarnessState";

interface ContextViewerProps {
  taskId: string | null;
  className?: string;
}

export function ContextViewer({ taskId, className = "" }: ContextViewerProps) {
  const task = useTask(taskId);

  if (!task) {
    return (
      <div className={className}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5" />
          Context
        </h2>
        <p className="text-sm text-gray-400 text-center py-8">No context available</p>
      </div>
    );
  }

  return (
    <div className={className}>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <Layers className="w-5 h-5" />
        Context
      </h2>
      <div className="space-y-3">
        {[
          { label: "Global", desc: "Coding standards, architecture rules", priority: "critical" },
          { label: "Task", desc: task.description, priority: "high" },
          { label: "Retrieved", desc: "RAG code snippets", priority: "medium" },
          { label: "Memory", desc: "Similar past tasks", priority: "low" },
        ].map((layer) => (
          <div
            key={layer.label}
            className="flex items-start gap-2 p-2 rounded border border-gray-100 dark:border-gray-800"
          >
            <FileCode className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  {layer.label}
                </span>
                <span
                  className={`text-[10px] uppercase px-1 rounded ${
                    layer.priority === "critical"
                      ? "bg-red-100 text-red-600"
                      : layer.priority === "high"
                      ? "bg-amber-100 text-amber-600"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {layer.priority}
                </span>
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 truncate">
                {layer.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
