import { useState, useCallback } from "react";
import { HarnessApi } from "../api/client";
import type { AuditEntry } from "../types/harness";

interface UseAuditLogOptions {
  sessionId?: string;
  limit?: number;
}

export function useAuditLogFetcher({ sessionId, limit = 100 }: UseAuditLogOptions = {}) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const fetchLog = useCallback(async () => {
    setLoading(true);
    try {
      const result = await HarnessApi.getAuditLog({
        session_id: sessionId,
        limit,
      });
      setEntries(
        result.entries.map((e) => ({
          entryId: e.entry_id,
          timestamp: e.timestamp,
          sessionId: e.session_id,
          action: e.action,
          actor: e.actor,
          result: e.result,
          riskLevel: e.risk_level,
        }))
      );
      setTotal(result.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch audit log");
    } finally {
      setLoading(false);
    }
  }, [sessionId, limit]);

  return { entries, total, loading, error, fetchLog };
}
