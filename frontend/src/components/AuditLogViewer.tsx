import { useEffect } from "react";
import { History } from "lucide-react";
import { useAuditLogFetcher } from "../hooks/useAuditLog";
import { formatDate } from "../utils/formatters";

interface AuditLogViewerProps {
  taskId: string | null;
  maxEntries?: number;
}

const riskColors: Record<string, string> = {
  low: "text-gray-500",
  medium: "text-amber-500",
  high: "text-orange-500",
  critical: "text-red-500",
};

export function AuditLogViewer({ taskId, maxEntries = 50 }: AuditLogViewerProps) {
  const { entries, loading, fetchLog } = useAuditLogFetcher({
    sessionId: taskId ?? undefined,
    limit: maxEntries,
  });

  useEffect(() => {
    fetchLog();
  }, [fetchLog]);

  return (
    <div>
      {loading && <p className="text-xs text-gray-400">Loading audit log...</p>}

      {!loading && entries.length === 0 && (
        <div className="text-center py-6 text-gray-400 dark:text-gray-500">
          <History className="w-5 h-5 mx-auto mb-1 opacity-50" />
          <p className="text-xs">No audit entries yet</p>
        </div>
      )}

      {entries.length > 0 && (
        <div className="space-y-1 max-h-[300px] overflow-y-auto">
          {entries.map((entry) => (
            <div
              key={entry.entryId}
              className="flex items-center gap-2 py-1.5 px-2 rounded text-xs border-b border-gray-100 dark:border-gray-800 last:border-0"
            >
              <span className={`font-medium w-12 shrink-0 ${riskColors[entry.riskLevel] ?? "text-gray-500"}`}>
                {entry.riskLevel.toUpperCase()}
              </span>
              <span className="truncate flex-1 font-medium text-gray-700 dark:text-gray-300">
                {entry.action}
              </span>
              <span className="text-gray-400 shrink-0">{formatDate(entry.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
