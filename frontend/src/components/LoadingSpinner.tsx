import { motion } from "framer-motion";

interface LoadingSpinnerProps {
  /** Size in pixels */
  size?: number;
  /** Optional message shown below spinner */
  message?: string;
}

/** Animated loading spinner with optional status message. */
export function LoadingSpinner({ size = 40, message }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      <motion.div
        style={{ width: size, height: size }}
        className="rounded-full border-4 border-blue-200 border-t-blue-600"
        animate={{ rotate: 360 }}
        transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
      />
      {message && (
        <motion.p
          className="text-sm text-gray-500"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {message}
        </motion.p>
      )}
    </div>
  );
}
