/**
 * Zustand store for Canvas page state.
 * Manages resume, metrics, pipeline, editing, and version history.
 */
import { create } from 'zustand';
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

  // ── Actions ───────────────────────────────
  setCanvasState: (state: CanvasState) => void;
  loadResume: (resume: Resume) => void;
  setJD: (jd: ParsedJD | null) => void;
  updateMetrics: (metrics: Partial<Metrics>) => void;
  setAgentState: (agent: AgentName, state: AgentState) => void;
  setPipelineRunning: (isRunning: boolean) => void;
  setEditingBullet: (bulletId: string | null) => void;
  updateBullet: (sectionId: string, bulletId: string, update: Partial<Bullet>) => void;
  addVersion: (version: VersionEntry) => void;
  setKeywords: (keywords: KeywordItem[]) => void;
  updateKeyword: (keyword: string, matched: boolean) => void;
  addChange: (change: ChangeData) => void;
  addEvent: (event: string) => void;
  reset: () => void;
}

export const useCanvasStore = create<CanvasStore>((set) => ({
  canvasState: 'EMPTY',
  resume: null,
  jd: null,
  metrics: { ...initialMetrics },
  pipeline: createInitialPipeline(),
  keywords: [],
  changes: [],
  events: [],
  editingBulletId: null,

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
      return { resume: { ...s.resume, sections } };
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
    }),
}));
