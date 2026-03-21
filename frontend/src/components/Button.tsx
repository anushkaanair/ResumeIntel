import { motion } from "framer-motion";

interface ButtonProps {
  /** Button label text */
  children: React.ReactNode;
  /** Click handler */
  onClick?: () => void;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Visual variant */
  variant?: "primary" | "secondary" | "ghost";
  /** Loading state - shows spinner */
  loading?: boolean;
  /** HTML button type */
  type?: "button" | "submit" | "reset";
  /** Additional CSS classes */
  className?: string;
}

/** Animated button with primary/secondary/ghost variants and loading state. */
export function Button({ children, onClick, disabled, variant = "primary", loading = false, type = "button", className = "" }: ButtonProps) {
  const base = "inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700",
    secondary: "bg-gray-100 text-gray-800 hover:bg-gray-200",
    ghost: "bg-transparent text-gray-600 hover:bg-gray-100",
  };

  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${className}`}
      whileTap={{ scale: 0.97 }}
    >
      {loading && (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </motion.button>
  );
}
