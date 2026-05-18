import type { ApprovalRequest } from "../types/harness";
import { ApprovalCard } from "./ApprovalCard";

interface ApprovalQueueProps {
  approvals: ApprovalRequest[];
  onApprove: (approvalId: string, approved: boolean, comment?: string) => void;
}

export function ApprovalQueue({ approvals, onApprove }: ApprovalQueueProps) {
  if (approvals.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 dark:text-gray-500">
        <p className="text-sm">No pending approvals</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
      {approvals.map((req) => (
        <ApprovalCard key={req.approvalId || req.id} request={req} onApprove={onApprove} />
      ))}
    </div>
  );
}
