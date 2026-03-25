/**
 * App-wide constants — agent names, color tiers, scoring thresholds.
 */
import type { AgentName, AgentState } from './types';

// ─── Agent display names ────────────────────────────────
export const AGENT_LABELS: Record<AgentName, string> = {
  A_ing: 'Ingestion',
  A_gen: 'Generation',
  A_qual: 'Quality',
  A_weak: 'Weak Detection',
  A_tail: 'Tailoring',
  A_int: 'Interview',
};

/** Ordered agent pipeline sequence (A_int runs in parallel, listed last). */
export const AGENT_PIPELINE_ORDER: AgentName[] = [
  'A_ing', 'A_gen', 'A_qual', 'A_weak', 'A_tail', 'A_int',
];

// ─── Agent pill colors (Tailwind classes) ───────────────
export const AGENT_STATE_COLORS: Record<AgentState, string> = {
  idle: 'bg-gray-300 text-gray-600',
  active: 'bg-blue-500 text-white animate-pulse',
  done: 'bg-green-500 text-white',
  failed: 'bg-red-500 text-white',
};

// ─── Score → color tiers ────────────────────────────────
export interface ScoreColorTier {
  bg: string;
  text: string;
  border: string;
  label: string;
}

export const SCORE_TIERS = {
  danger:  { bg: 'bg-red-50',    text: 'text-red-600',    border: 'border-red-200',    label: 'Low' },
  warning: { bg: 'bg-amber-50',  text: 'text-amber-600',  border: 'border-amber-200',  label: 'Fair' },
  success: { bg: 'bg-green-50',  text: 'text-green-600',  border: 'border-green-200',  label: 'Good' },
} as const;

/** Thresholds for the metrics sidebar progress bar colors. */
export const SCORE_THRESHOLDS = {
  DANGER_MAX: 0.55,
  WARNING_MAX: 0.73,
} as const;

// ─── Bullet impact score badge colors ───────────────────
export const IMPACT_TIERS = {
  low:    { bg: 'bg-red-50',   text: 'text-red-600',   max: 0.39 },
  medium: { bg: 'bg-amber-50', text: 'text-amber-600', max: 0.69 },
  high:   { bg: 'bg-green-50', text: 'text-green-600', max: 1.0 },
} as const;

// ─── Practice feedback score tiers ──────────────────────
export const PRACTICE_SCORE_TIERS = {
  poor:      { bg: 'bg-red-50',     text: 'text-red-600',     max: 39 },
  fair:      { bg: 'bg-amber-50',   text: 'text-amber-600',   max: 69 },
  good:      { bg: 'bg-green-50',   text: 'text-green-600',   max: 89 },
  excellent: { bg: 'bg-emerald-50', text: 'text-emerald-700', max: 100 },
} as const;

// ─── Gap type badges ────────────────────────────────────
export const GAP_TYPE_STYLES = {
  missing_skill:   { bg: 'bg-red-50',    text: 'text-red-700',    label: 'Missing skill' },
  depth_mismatch:  { bg: 'bg-amber-50',  text: 'text-amber-700',  label: 'Depth gap' },
  missing_domain:  { bg: 'bg-purple-50', text: 'text-purple-700', label: 'Domain gap' },
  recency_gap:     { bg: 'bg-blue-50',   text: 'text-blue-700',   label: 'Recency gap' },
} as const;

// ─── Gap severity dot colors ────────────────────────────
export const GAP_SEVERITY_COLORS = {
  high:   'bg-red-500',
  medium: 'bg-amber-500',
  low:    'bg-green-500',
} as const;

// ─── Question category tab colors ───────────────────────
export const CATEGORY_TAB_COLORS = {
  all:              { active: 'bg-gray-900 text-white',        inactive: 'bg-gray-100 text-gray-600 hover:bg-gray-200' },
  technical:        { active: 'bg-purple-100 text-purple-800', inactive: 'bg-gray-100 text-gray-600 hover:bg-gray-200' },
  behavioral:       { active: 'bg-teal-100 text-teal-800',     inactive: 'bg-gray-100 text-gray-600 hover:bg-gray-200' },
  role_specific:    { active: 'bg-orange-100 text-orange-800', inactive: 'bg-gray-100 text-gray-600 hover:bg-gray-200' },
  company_specific: { active: 'bg-amber-100 text-amber-800',  inactive: 'bg-gray-100 text-gray-600 hover:bg-gray-200' },
} as const;

// ─── Difficulty colors ──────────────────────────────────
export const DIFFICULTY_COLORS = {
  easy:   'bg-green-500',
  medium: 'bg-amber-500',
  hard:   'bg-red-500',
} as const;

// ─── Skill tag colors ───────────────────────────────────
export const SKILL_TAG_MATCHED   = 'bg-green-50 text-green-700 border-green-200';
export const SKILL_TAG_UNMATCHED = 'bg-gray-100 text-gray-700 border-gray-200';

// ─── Animation durations (ms) ───────────────────────────
export const ANIM = {
  CROSSFADE: 400,
  SHIMMER: 1500,
  SCORE_PULSE: 800,
  METRIC_BAR: 600,
  SECTION_HOVER: 200,
  EDIT_APPEAR: 150,
  SKILL_POP: 300,
  JD_COLLAPSE: 300,
  GREEN_BORDER: 5000,
  AMBER_BORDER: 5000,
  BORDER_FLASH: 600,
  SCALE_POP: 600,
  SUGGESTION_SLIDE: 300,
  QUESTION_EXPAND: 300,
  QUESTION_COLLAPSE: 200,
  FEEDBACK_APPEAR: 400,
} as const;

// ─── API base ───────────────────────────────────────────
export const API_BASE = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000/api/v1';
export const WS_BASE = (import.meta as any).env.VITE_WS_URL || 'ws://localhost:8000/ws';

// ─── Misc ───────────────────────────────────────────────
export const MAX_UNDO_DEPTH = 50;
export const EDIT_DEBOUNCE_MS = 30_000; // 30s debounce for version creation
export const PRACTICE_MIN_CHARS = 320;
export const WS_RECONNECT_MAX_MS = 30_000;
