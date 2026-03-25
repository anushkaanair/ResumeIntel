/**
 * Zustand store for Interview Prep page state.
 * Manages questions, gaps, practice mode, and filtering.
 */
import { create } from 'zustand';
import type {
  InterviewPageState,
  InterviewData,
  QuestionCategory,
  Difficulty,
  PracticeFeedback,
} from '../lib/types';

export interface InterviewStore {
  // ── Core state ────────────────────────────
  pageState: InterviewPageState;
  data: InterviewData | null;

  // ── Filters ───────────────────────────────
  activeCategory: QuestionCategory | 'all';
  activeDifficulty: Difficulty | 'all';

  // ── Expansion / Practice ──────────────────
  expandedQuestionId: string | null;
  practicingQuestionId: string | null;
  currentFeedback: PracticeFeedback | null;

  // ── Actions ───────────────────────────────
  setPageState: (state: InterviewPageState) => void;
  loadData: (data: InterviewData) => void;
  setCategory: (cat: QuestionCategory | 'all') => void;
  setDifficulty: (diff: Difficulty | 'all') => void;
  toggleQuestion: (questionId: string) => void;
  startPractice: (questionId: string) => void;
  endPractice: () => void;
  setFeedback: (feedback: PracticeFeedback) => void;
  reset: () => void;
}

export const useInterviewStore = create<InterviewStore>((set) => ({
  pageState: 'not_generated',
  data: null,
  activeCategory: 'all',
  activeDifficulty: 'all',
  expandedQuestionId: null,
  practicingQuestionId: null,
  currentFeedback: null,

  setPageState: (pageState) => set({ pageState }),

  loadData: (data) => set({ data, pageState: 'ready' }),

  setCategory: (activeCategory) => set({ activeCategory }),

  setDifficulty: (activeDifficulty) => set({ activeDifficulty }),

  toggleQuestion: (questionId) =>
    set((s) => ({
      expandedQuestionId: s.expandedQuestionId === questionId ? null : questionId,
    })),

  startPractice: (questionId) =>
    set({ practicingQuestionId: questionId, currentFeedback: null, pageState: 'practicing' }),

  endPractice: () =>
    set({ practicingQuestionId: null, currentFeedback: null, pageState: 'ready' }),

  setFeedback: (currentFeedback) => set({ currentFeedback }),

  reset: () =>
    set({
      pageState: 'not_generated',
      data: null,
      activeCategory: 'all',
      activeDifficulty: 'all',
      expandedQuestionId: null,
      practicingQuestionId: null,
      currentFeedback: null,
    }),
}));
