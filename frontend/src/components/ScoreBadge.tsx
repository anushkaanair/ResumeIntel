import { motion } from "framer-motion";

interface ScoreBadgeProps {
  /** Score value between 0 and 1 */
  score: number;
  /** Label for the score */
  label: string;
}

/** Small badge showing a named score with color coding. */
export function ScoreBadge({ score, label }: ScoreBadgeProps) {
  const percentage = Math.round(score * 100);
  const colorClass = score >= 0.75
    ? "bg-green-100 text-green-800 border-green-200"
    : score >= 0.5
    ? "bg-yellow-100 text-yellow-800 border-yellow-200"
    : "bg-red-100 text-red-800 border-red-200";

  return (
    <motion.div
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium ${colorClass}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <span>{label}</span>
      <span className="font-bold">{percentage}%</span>
    </motion.div>
  );
}
