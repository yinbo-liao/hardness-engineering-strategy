import type { ConnectionStatus as ConnectionStatusType } from "../types/harness";

const config: Record<ConnectionStatusType, { dot: string; label: string }> = {
  connected: { dot: "bg-green-500", label: "Connected" },
  connecting: { dot: "bg-amber-500 animate-pulse", label: "Connecting" },
  reconnecting: { dot: "bg-amber-500 animate-pulse", label: "Reconnecting" },
  disconnected: { dot: "bg-red-500", label: "Disconnected" },
};

export function ConnectionStatus({ status }: { status: ConnectionStatusType }) {
  const c = config[status] ?? config.disconnected;
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
      <span className={`inline-block w-2 h-2 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}
