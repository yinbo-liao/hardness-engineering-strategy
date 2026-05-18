import { useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { isValidTaskDescription } from "../utils/validators";

interface TaskSubmissionFormProps {
  onSubmit: (description: string, taskType: string) => Promise<void>;
}

const TASK_TYPES = [
  { value: "code", label: "Code" },
  { value: "test", label: "Test" },
  { value: "review", label: "Review" },
  { value: "deploy", label: "Deploy" },
  { value: "fix", label: "Fix" },
];

export function TaskSubmissionForm({ onSubmit }: TaskSubmissionFormProps) {
  const [description, setDescription] = useState("");
  const [taskType, setTaskType] = useState("code");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!isValidTaskDescription(description)) return;
    setSubmitting(true);
    try {
      await onSubmit(description, taskType);
      setDescription("");
    } finally {
      setSubmitting(false);
    }
  };

  const isValid = isValidTaskDescription(description);

  return (
    <div className="space-y-3">
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Describe what you want to build... (e.g., 'Add a FastAPI endpoint for user login with JWT auth')"
        rows={3}
        className="w-full px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none placeholder:text-gray-400"
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
        }}
      />

      <div className="flex items-center gap-3">
        <select
          value={taskType}
          onChange={(e) => setTaskType(e.target.value)}
          className="px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {TASK_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        <button
          onClick={handleSubmit}
          disabled={!isValid || submitting}
          className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          Submit Task
        </button>

        {!isValid && description.length > 0 && (
          <p className="text-xs text-amber-500">Min 5 characters required</p>
        )}
      </div>
    </div>
  );
}
