import type { Task } from "../types/harness";
import { TaskCard } from "./TaskCard";

interface TaskListProps {
  tasks: Task[];
  selectedTask: string | null;
  onSelectTask: (id: string) => void;
}

export function TaskList({ tasks, selectedTask, onSelectTask }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400 dark:text-gray-500">
        <p className="text-lg font-medium">No tasks yet</p>
        <p className="text-sm mt-1">Submit a task to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          selected={selectedTask === task.id}
          onSelect={onSelectTask}
        />
      ))}
    </div>
  );
}
