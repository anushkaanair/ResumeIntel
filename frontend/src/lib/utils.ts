/**
 * Utility helpers — score→color, formatting, etc.
 */
import {
  SCORE_THRESHOLDS,
  SCORE_TIERS,
  IMPACT_TIERS,
  PRACTICE_SCORE_TIERS,
  type ScoreColorTier,
} from './constants';

/** Returns the color tier (danger/warning/success) for a 0–1 or 0–100 score. */
export function getScoreTier(score: number, maxIs100 = false): ScoreColorTier {
  const normalized = maxIs100 ? score / 100 : score;
  if (normalized < SCORE_THRESHOLDS.DANGER_MAX) return SCORE_TIERS.danger;
  if (normalized < SCORE_THRESHOLDS.WARNING_MAX) return SCORE_TIERS.warning;
  return SCORE_TIERS.success;
}

/** Returns impact badge classes for a 0–1 impact score. */
export function getImpactClasses(score: number): { bg: string; text: string } {
  if (score <= IMPACT_TIERS.low.max) return IMPACT_TIERS.low;
  if (score <= IMPACT_TIERS.medium.max) return IMPACT_TIERS.medium;
  return IMPACT_TIERS.high;
}

/** Returns practice feedback score classes for 0–100 score. */
export function getPracticeScoreClasses(score: number): { bg: string; text: string } {
  if (score <= PRACTICE_SCORE_TIERS.poor.max) return PRACTICE_SCORE_TIERS.poor;
  if (score <= PRACTICE_SCORE_TIERS.fair.max) return PRACTICE_SCORE_TIERS.fair;
  if (score <= PRACTICE_SCORE_TIERS.good.max) return PRACTICE_SCORE_TIERS.good;
  return PRACTICE_SCORE_TIERS.excellent;
}

/** Formats a 0–1 score as percentage string (e.g. "73%"). */
export function formatPct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Formats a 0–100 score as percentage string (e.g. "73%"). */
export function formatPct100(score: number): string {
  return `${Math.round(score)}%`;
}

/** Formats a 0–1 score as "0.73" with 2 decimals. */
export function formatScore(score: number): string {
  return score.toFixed(2);
}

/** Generates a UUID-like random string. */
export function generateId(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/** Clamps a number between min and max. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Simple debounce helper. */
export function debounce<T extends (...args: unknown[]) => void>(fn: T, ms: number): T {
  let timer: ReturnType<typeof setTimeout>;
  return ((...args: unknown[]) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  }) as T;
}

/** Check if user prefers reduced motion. */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
