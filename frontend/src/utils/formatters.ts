export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function truncate(str: string, maxLen: number = 80): string {
  return str.length <= maxLen ? str : str.slice(0, maxLen) + "...";
}

export function statusColor(status: string): string {
  switch (status) {
    case "completed": return "text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30";
    case "running": return "text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30";
    case "failed": return "text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30";
    case "queued": return "text-amber-600 bg-amber-100 dark:text-amber-400 dark:bg-amber-900/30";
    default: return "text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-700";
  }
}
