import { CheckCircle2, XCircle, BarChart3 } from "lucide-react";
import { useTask } from "../hooks/useHarnessState";
import { formatPercent } from "../utils/formatters";

interface EvaluationResultsProps {
  taskId: string | null;
  className?: string;
}

const dimensionLabels: Record<string, string> = {
  unit_tests: "Unit Tests",
  type_check: "Type Safety",
  lint: "Code Style",
  security_scan: "Security",
  architecture: "Architecture",
  performance: "Performance",
};

export function EvaluationResults({ taskId, className = "" }: EvaluationResultsProps) {
  const task = useTask(taskId);

  if (!task || task.status !== "completed") {
    return (
      <div className={className}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          Evaluation
        </h2>
        <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">
          Results appear when a task completes
        </p>
      </div>
    );
  }

  // Use stub dimensions for display when real data isn't available
  const dimensions = (task.result as any)?.evaluation?.dimensions ?? {};

  return (
    <div className={className}>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <BarChart3 className="w-5 h-5" />
        Evaluation
      </h2>
      <div className="space-y-2">
        {Object.entries(dimensions).length === 0 ? (
          <p className="text-sm text-gray-400">No dimension data available</p>
        ) : (
          Object.entries(dimensions).map(([key, dim]: [string, any]) => (
            <div
              key={key}
              className="flex items-center justify-between p-2 rounded border border-gray-100 dark:border-gray-800"
            >
              <div className="flex items-center gap-2">
                {dim.passed ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {dimensionLabels[key] ?? key}
                </span>
              </div>
              <span
                className={`text-xs font-medium ${
                  dim.passed ? "text-green-600" : "text-red-600"
                }`}
              >
                {formatPercent(dim.score)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
