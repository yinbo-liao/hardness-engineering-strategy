interface FilterButtonProps {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
  badgeColor?: string;
}

export function FilterButton({ active, onClick, label, count, badgeColor = "blue" }: FilterButtonProps) {
  const activeClass = active
    ? "bg-blue-600 text-white"
    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600";

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${activeClass}`}
    >
      {label}
      <span
        className={`px-1.5 py-0.5 text-xs rounded-full ${
          active
            ? "bg-white/20 text-white"
            : `bg-${badgeColor}-100 text-${badgeColor}-800 dark:bg-${badgeColor}-900/30 dark:text-${badgeColor}-400`
        }`}
      >
        {count}
      </span>
    </button>
  );
}
