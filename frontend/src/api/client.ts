import type { paths } from "./harness";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

function getAuthToken(): string {
  return localStorage.getItem("harness_auth_token") || "";
}

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => undefined);
    throw new ApiError(response.status, response.statusText, errorData);
  }

  return response.json();
}

export const HarnessApi = {
  createTask: (
    data: paths["/api/v1/harness/tasks"]["post"]["requestBody"]["content"]["application/json"]
  ) =>
    fetchApi<
      paths["/api/v1/harness/tasks"]["post"]["responses"][200]["content"]["application/json"]
    >("/api/v1/harness/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getTaskStatus: (taskId: string) =>
    fetchApi<
      paths["/api/v1/harness/tasks/{task_id}"]["get"]["responses"][200]["content"]["application/json"]
    >(`/api/v1/harness/tasks/${taskId}`),

  getAuditLog: (params?: {
    session_id?: string;
    start_time?: string;
    end_time?: string;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.append(key, String(value));
      });
    }
    return fetchApi<
      paths["/api/v1/harness/audit"]["get"]["responses"][200]["content"]["application/json"]
    >(`/api/v1/harness/audit?${searchParams.toString()}`);
  },
};

export { ApiError };
