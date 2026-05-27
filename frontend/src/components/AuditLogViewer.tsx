import { useState, useEffect, useCallback } from "react";
import { History } from "lucide-react";
import { formatDate } from "../utils/formatters";

interface AuditLogViewerProps {
  taskId?: string | null;
  maxEntries?: number;
}

const riskColors: Record<string, string> = {
  low: "text-gray-500",
  medium: "text-amber-500",
  high: "text-orange-500",
  critical: "text-red-500",
};

export function AuditLogViewer({ maxEntries = 50 }: AuditLogViewerProps) {
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLog = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/Hardness/audit?limit=${maxEntries}`);
      if (res.ok) {
        const data = await res.json();
        setEntries(data.entries || []);
      }
    } catch {} finally {
      setLoading(false);
    }
  }, [maxEntries]);

  useEffect(() => {
    fetchLog();
    const interval = setInterval(fetchLog, 3000);
    return () => clearInterval(interval);
  }, [fetchLog]);

  return (
    <div>
      {loading && entries.length === 0 && (
        <p className="text-xs text-gray-400">Loading audit log...</p>
      )}

      {!loading && entries.length === 0 && (
        <div className="text-center py-6 text-gray-400 dark:text-gray-500">
          <History className="w-5 h-5 mx-auto mb-1 opacity-50" />
          <p className="text-xs">No audit entries yet</p>
        </div>
      )}

      {entries.length > 0 && (
        <div className="space-y-1 max-h-[300px] overflow-y-auto">
          {entries.map((entry, i) => (
            <div
              key={`${entry.entry_id || entry.timestamp}-${i}`}
              className="flex items-center gap-2 py-1.5 px-2 rounded text-xs border-b border-gray-100 dark:border-gray-800 last:border-0"
            >
              <span className={`font-medium w-12 shrink-0 ${riskColors[entry.risk_level] ?? "text-gray-500"}`}>
                {(entry.risk_level || "low").toUpperCase()}
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
