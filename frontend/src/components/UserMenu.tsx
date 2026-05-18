import { User } from "lucide-react";

export function UserMenu() {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
      <User className="w-5 h-5" />
      <span className="hidden sm:inline">Operator</span>
    </div>
  );
}
