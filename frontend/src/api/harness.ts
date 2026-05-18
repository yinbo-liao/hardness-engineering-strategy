export interface paths {
  "/api/v1/harness/tasks": {
    post: {
      requestBody: {
        content: {
          "application/json": {
            task_id?: string;
            description: string;
            task_type: "code" | "test" | "review" | "deploy" | "fix";
            dependencies?: string[];
            priority?: number;
            timeout_seconds?: number;
          };
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              status: string;
              task_id: string;
              queue_position?: number;
            };
          };
        };
      };
    };
  };
  "/api/v1/harness/tasks/{task_id}": {
    get: {
      parameters: { path: { task_id: string } };
      responses: {
        200: {
          content: {
            "application/json": {
              task_id: string;
              status: string;
              description: string;
              type: string;
              result?: Record<string, unknown>;
              error_log?: string[];
              retry_count: number;
              created_at: string;
              updated_at: string;
            };
          };
        };
      };
    };
  };
  "/api/v1/harness/audit": {
    get: {
      parameters: {
        query: {
          session_id?: string;
          start_time?: string;
          end_time?: string;
          limit?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              entries: Array<{
                entry_id: string;
                timestamp: string;
                session_id: string;
                action: string;
                actor: string;
                result: string;
                risk_level: string;
              }>;
              total: number;
              page: number;
            };
          };
        };
      };
    };
  };
}

export type TaskRequest = paths["/api/v1/harness/tasks"]["post"]["requestBody"]["content"]["application/json"];
export type TaskCreateResponse = paths["/api/v1/harness/tasks"]["post"]["responses"][200]["content"]["application/json"];
export type TaskStatusResponse = paths["/api/v1/harness/tasks/{task_id}"]["get"]["responses"][200]["content"]["application/json"];
export type AuditLogResponse = paths["/api/v1/harness/audit"]["get"]["responses"][200]["content"]["application/json"];
