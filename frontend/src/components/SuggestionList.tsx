import { motion } from "framer-motion";

interface SuggestionListProps {
  /** List of suggestion strings */
  suggestions: string[];
  /** Section title */
  title?: string;
}

/** Animated list of improvement suggestions. */
export function SuggestionList({ suggestions, title = "Suggestions" }: SuggestionListProps) {
  if (suggestions.length === 0) return null;

  return (
    <div>
      <h4 className="mb-3 font-semibold text-gray-700">{title}</h4>
      <ul className="space-y-2">
        {suggestions.map((suggestion, idx) => (
          <motion.li
            key={idx}
            className="flex items-start gap-2 rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-800 border border-amber-200"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            <span className="mt-0.5 text-amber-500">⚠</span>
            {suggestion}
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
