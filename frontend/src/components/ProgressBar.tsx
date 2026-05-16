interface Props {
  current: number;
  total: number;
}

export default function ProgressBar({ current, total }: Props) {
  const pct = Math.min(100, (current / total) * 100);
  return (
    <div className="w-full max-w-xs mx-auto">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>已看 {current}</span>
        <span>共 {total}</span>
      </div>
      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-amber-400 to-rose-400 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
