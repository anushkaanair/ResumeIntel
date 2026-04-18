/**
 * Zustand store for Canvas page state.
 * Manages resume, metrics, pipeline, editing, and version history.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  CanvasState,
  Resume,
  ResumeSection,
  ParsedJD,
  Metrics,
  PipelineState,
  AgentName,
  AgentState,
  Bullet,
  VersionEntry,
  ChangeData,
  KeywordItem,
} from '../lib/types';
import { AGENT_PIPELINE_ORDER } from '../lib/constants';

function createInitialPipeline(): PipelineState {
  const agents = {} as Record<AgentName, AgentState>;
  for (const name of AGENT_PIPELINE_ORDER) {
    agents[name] = 'idle';
  }
  return { agents, currentAgent: null, isRunning: false };
}

const initialMetrics: Metrics = {
  alignment: 0,
  keywordCoverage: 0,
  impactScore: 0,
  atsPassRate: 0,
  source: 'LOCAL',
};

// ── Per-bullet undo stack ─────────────────────────────────────────────────

interface UndoEntry {
  timestamp: number;
  action: string;
  previousStatus: Bullet['status'];
  previousContent: string;
}

// ── Provenance (mirrors backend Provenance dataclass) ─────────────────────

export interface BulletProvenance {
  agent_name: string;
  input_summary: string;
  retrieved_chunks: string[];
  decision_rationale: string;
  confidence: number;
}

export interface CanvasStore {
  // ── Core state ────────────────────────────
  canvasState: CanvasState;
  resume: Resume | null;
  jd: ParsedJD | null;
  metrics: Metrics;
  pipeline: PipelineState;
  keywords: KeywordItem[];
  changes: ChangeData[];
  events: string[];

  // ── Editing state ─────────────────────────
  editingBulletId: string | null;

  // ── Bullet-level undo stacks (persist across page refresh) ────────────
  bulletUndoStacks: Record<string, UndoEntry[]>;

  // ── Provenance map (bulletId → Provenance) ────────────────────────────
  bulletProvenance: Record<string, BulletProvenance>;

  // ── Actions ───────────────────────────────
  setCanvasState: (state: CanvasState) => void;
  loadResume: (resume: Resume) => void;
  setJD: (jd: ParsedJD | null) => void;
  updateMetrics: (metrics: Partial<Metrics>) => void;
  setAgentState: (agent: AgentName, state: AgentState) => void;
  setPipelineRunning: (isRunning: boolean) => void;
  setEditingBullet: (bulletId: string | null) => void;
  updateBullet: (sectionId: string, bulletId: string, update: Partial<Bullet>) => void;
  undoBullet: (sectionId: string, bulletId: string) => void;
  addVersion: (version: VersionEntry) => void;
  setKeywords: (keywords: KeywordItem[]) => void;
  updateKeyword: (keyword: string, matched: boolean) => void;
  addChange: (change: ChangeData) => void;
  addEvent: (event: string) => void;
  setBulletProvenance: (bulletId: string, provenance: BulletProvenance) => void;
  reset: () => void;
}

export const useCanvasStore = create<CanvasStore>()(
  persist(
    (set, _get) => ({
  canvasState: 'EMPTY',
  resume: null,
  jd: null,
  metrics: { ...initialMetrics },
  pipeline: createInitialPipeline(),
  keywords: [],
  changes: [],
  events: [],
  editingBulletId: null,
  bulletUndoStacks: {},
  bulletProvenance: {},

  setCanvasState: (canvasState) => set({ canvasState }),

  loadResume: (resume) => set({ resume, canvasState: 'LOADED' }),

  setJD: (jd) => set({ jd }),

  updateMetrics: (partial) =>
    set((s) => ({ metrics: { ...s.metrics, ...partial, lastUpdated: new Date().toISOString() } })),

  setAgentState: (agent, state) =>
    set((s) => ({
      pipeline: {
        ...s.pipeline,
        agents: { ...s.pipeline.agents, [agent]: state },
        currentAgent: state === 'active' ? agent : s.pipeline.currentAgent,
      },
    })),

  setPipelineRunning: (isRunning) =>
    set((s) => ({
      pipeline: { ...s.pipeline, isRunning },
      canvasState: isRunning ? 'OPTIMIZING' : s.canvasState,
    })),

  setEditingBullet: (editingBulletId) =>
    set({ editingBulletId, canvasState: editingBulletId ? 'EDITING' : 'LOADED' }),

  updateBullet: (sectionId, bulletId, update) =>
    set((s) => {
      if (!s.resume) return {};

      // Record current state to undo stack before applying update
      let prevContent = '';
      let prevStatus: Bullet['status'] = 'original';
      for (const sec of s.resume.sections) {
        if (sec.id !== sectionId) continue;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const entries = (sec.content as any).entries ?? [];
        for (const entry of entries) {
          const bullet = entry.bullets?.find((b: Bullet) => b.id === bulletId);
          if (bullet) { prevContent = bullet.currentText; prevStatus = bullet.status; }
        }
      }

      const prevStack = s.bulletUndoStacks[bulletId] ?? [];
      const newEntry: UndoEntry = {
        timestamp: Date.now(),
        action: Object.keys(update).join(','),
        previousStatus: prevStatus,
        previousContent: prevContent,
      };

      const sections = s.resume.sections.map((sec) => {
        if (sec.id !== sectionId) return sec;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const content = sec.content as any;
        if (!content.entries) return sec;
        return {
          ...sec,
          content: {
            ...content,
            entries: content.entries.map((entry: any) => ({
              ...entry,
              bullets: entry.bullets?.map((b: Bullet) =>
                b.id === bulletId ? { ...b, ...update } : b
              ),
            })),
          },
        };
      }) as ResumeSection[];

      return {
        resume: { ...s.resume, sections },
        bulletUndoStacks: {
          ...s.bulletUndoStacks,
          [bulletId]: [...prevStack, newEntry],
        },
      };
    }),

  undoBullet: (sectionId, bulletId) =>
    set((s) => {
      if (!s.resume) return {};
      const stack = s.bulletUndoStacks[bulletId] ?? [];
      if (stack.length === 0) return {};

      const last = stack[stack.length - 1];
      const sections = s.resume.sections.map((sec) => {
        if (sec.id !== sectionId) return sec;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const content = sec.content as any;
        if (!content.entries) return sec;
        return {
          ...sec,
          content: {
            ...content,
            entries: content.entries.map((entry: any) => ({
              ...entry,
              bullets: entry.bullets?.map((b: Bullet) =>
                b.id === bulletId
                  ? { ...b, currentText: last.previousContent, status: last.previousStatus }
                  : b
              ),
            })),
          },
        };
      }) as ResumeSection[];

      return {
        resume: { ...s.resume, sections },
        bulletUndoStacks: {
          ...s.bulletUndoStacks,
          [bulletId]: stack.slice(0, -1),
        },
      };
    }),

  addVersion: (version) =>
    set((s) => {
      if (!s.resume) return {};
      return {
        resume: {
          ...s.resume,
          versions: [...s.resume.versions, version],
          currentVersion: version.versionNum,
        },
      };
    }),

  setKeywords: (keywords) => set({ keywords }),

  updateKeyword: (keyword, matched) =>
    set((s) => ({
      keywords: s.keywords.map((k) =>
        k.keyword === keyword ? { ...k, matched } : k
      ),
    })),

  addChange: (change) => set((s) => ({ changes: [...s.changes, change] })),

  addEvent: (event) => set((s) => ({ events: [...s.events, event] })),

  setBulletProvenance: (bulletId, provenance) =>
    set((s) => ({ bulletProvenance: { ...s.bulletProvenance, [bulletId]: provenance } })),

  reset: () =>
    set({
      canvasState: 'EMPTY',
      resume: null,
      jd: null,
      metrics: { ...initialMetrics },
      pipeline: createInitialPipeline(),
      keywords: [],
      changes: [],
      events: [],
      editingBulletId: null,
      bulletUndoStacks: {},
      bulletProvenance: {},
    }),
}),
    {
      name: 'resume-intel-canvas',          // localStorage key
      partialize: (s) => ({                 // only persist undo stacks + provenance
        bulletUndoStacks: s.bulletUndoStacks,
        bulletProvenance: s.bulletProvenance,
      }),
    }
  )
);
