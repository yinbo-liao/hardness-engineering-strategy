import { useState, useEffect, useRef } from "react";
import { HarnessApi } from "../api/client";

interface UseTaskPollingOptions {
  taskId: string | null;
  intervalMs?: number;
  enabled?: boolean;
}

export function useTaskPolling({ taskId, intervalMs = 5000, enabled = true }: UseTaskPollingOptions) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!taskId || !enabled) {
      setData(null);
      return;
    }

    const fetchStatus = async () => {
      setLoading(true);
      try {
        const result = await HarnessApi.getTaskStatus(taskId);
        setData(result as unknown as Record<string, unknown>);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to fetch task status");
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    timerRef.current = setInterval(fetchStatus, intervalMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [taskId, intervalMs, enabled]);

  return { data, error, loading };
}
