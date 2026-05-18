import { Check, X, ShieldAlert } from "lucide-react";
import type { ApprovalRequest } from "../types/harness";
import { formatDate } from "../utils/formatters";

const riskColors: Record<string, string> = {
  low: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

interface ApprovalCardProps {
  request: ApprovalRequest;
  onApprove: (id: string, approved: boolean, comment?: string) => void;
}

export function ApprovalCard({ request, onApprove }: ApprovalCardProps) {
  const riskClass = riskColors[request.riskLevel] ?? riskColors.low;

  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert className="w-4 h-4 text-red-500" />
            <span className={`px-1.5 py-0.5 rounded text-xs font-medium uppercase ${riskClass}`}>
              {request.riskLevel}
            </span>
          </div>
          <p className="font-medium text-gray-900 dark:text-white text-sm">
            {request.action}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatDate(request.requestedAt)}
          </p>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onApprove(request.approvalId || request.id, true)}
            className="p-1.5 rounded-lg text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
            title="Approve"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={() => onApprove(request.approvalId || request.id, false, "Rejected")}
            className="p-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            title="Reject"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
