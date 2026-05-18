export type TaskStatus = "pending" | "queued" | "running" | "completed" | "failed";
export type TaskType = "code" | "test" | "review" | "deploy" | "fix";
export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";
export type LoopPhase =
  | "task_started"
  | "iteration_started"
  | "phase_reasoning"
  | "phase_action"
  | "execution_completed"
  | "evaluation_completed"
  | "phase_feedback"
  | "task_completed"
  | "task_failed";

export interface Task {
  id: string;
  description: string;
  type: TaskType;
  status: TaskStatus;
  progress: number;
  currentIteration: number;
  maxIterations: number;
  currentPhase?: LoopPhase;
  createdAt: string;
  logs: LogEntry[];
  result?: Record<string, unknown>;
  errorLog?: string[];
}

export interface LogEntry {
  timestamp: string;
  level: "info" | "warning" | "error";
  message: string;
  tool?: string;
}

export interface ApprovalRequest {
  id: string;
  approvalId: string;
  sessionId: string;
  action: string;
  params: Record<string, unknown>;
  riskLevel: "low" | "medium" | "high" | "critical";
  requestedAt: string;
  timeoutAt: string;
}

export interface SystemMetrics {
  activeTasks: number;
  queuedTasks: number;
  completedTasks: number;
  failedTasks: number;
  avgExecutionTime: number;
  systemLoad: number;
  memoryUsage: number;
}

export interface AuditEntry {
  entryId: string;
  timestamp: string;
  sessionId: string;
  action: string;
  actor: string;
  result: string;
  riskLevel: string;
}

export interface HarnessEvent {
  type: string;
  payload: {
    task_id?: string;
    taskId?: string;
    approval_id?: string;
    message?: string;
    [key: string]: unknown;
  };
}

export interface EvaluationDimensionResult {
  passed: boolean;
  score: number;
  details: Record<string, unknown>;
  logs: string[];
}

export interface EvaluationResult {
  passed: boolean;
  weightedScore: number;
  dimensions: Record<string, EvaluationDimensionResult>;
  summary: string;
  feedback?: {
    failedDimensions: string[];
    suggestedFixes: string[];
    fixPriority: string[];
  };
}
