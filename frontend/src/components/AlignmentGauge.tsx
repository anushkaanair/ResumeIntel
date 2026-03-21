import { motion } from "framer-motion";

interface AlignmentGaugeProps {
  /** Alignment score between 0 and 1 */
  score: number;
  /** Label shown below the gauge */
  label?: string;
}

/** Visual gauge showing resume-JD alignment score. */
export function AlignmentGauge({ score, label = "Alignment" }: AlignmentGaugeProps) {
  const percentage = Math.round(score * 100);
  const color = score >= 0.75 ? "text-green-500" : score >= 0.5 ? "text-yellow-500" : "text-red-500";
  const bgColor = score >= 0.75 ? "bg-green-100" : score >= 0.5 ? "bg-yellow-100" : "bg-red-100";

  return (
    <div className={`flex flex-col items-center gap-2 rounded-xl p-6 ${bgColor}`}>
      <motion.div
        className={`text-5xl font-bold ${color}`}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 200 }}
      >
        {percentage}%
      </motion.div>
      <span className="text-sm font-medium text-gray-600">{label}</span>
    </div>
  );
}
