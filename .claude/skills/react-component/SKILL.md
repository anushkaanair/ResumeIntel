---
name: react-component
description: Create React components for the resume intelligence dashboard. Use when building UI components, pages, or interactive elements for the frontend. Triggers on "component", "dashboard", "UI for", "frontend widget", "React page".
---

# React Component Pattern

```tsx
import { useState } from "react";
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

  return (
    <div className="flex flex-col items-center gap-2">
      <motion.div
        className={`text-4xl font-bold ${color}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {percentage}%
      </motion.div>
      <span className="text-sm text-gray-500">{label}</span>
    </div>
  );
}
```

## Rules
- Named export, never default export
- Props interface with JSDoc on each prop
- JSDoc on the component itself
- Tailwind utility classes only
- Framer Motion for animations
- Loading + error states for async components
- API calls through lib/api.ts, not inline fetch
