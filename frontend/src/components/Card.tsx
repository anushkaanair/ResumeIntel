import { motion } from "framer-motion";

interface CardProps {
  /** Card title */
  title?: string;
  /** Card content */
  children: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
}

/** Animated card container with optional title. */
export function Card({ title, children, className = "" }: CardProps) {
  return (
    <motion.div
      className={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm ${className}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {title && <h3 className="mb-4 text-lg font-semibold text-gray-800">{title}</h3>}
      {children}
    </motion.div>
  );
}
