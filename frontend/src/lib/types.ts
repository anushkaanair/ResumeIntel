/**
 * V2 TypeScript interfaces — Canvas, Interview, Pipeline, Scoring.
 * All types used across stores, hooks, components, and API calls.
 */

// ─── Agent & Pipeline ───────────────────────────────────
export type AgentName = 'A_ing' | 'A_gen' | 'A_qual' | 'A_weak' | 'A_tail' | 'A_int';
export type AgentState = 'idle' | 'active' | 'done' | 'failed';
export type CanvasState = 'EMPTY' | 'LOADED' | 'IDLE' | 'OPTIMIZING' | 'OPTIMIZED' | 'RE_OPTIMIZING' | 'EDITING' | 'ERROR';

export interface PipelineState {
  agents: Record<AgentName, AgentState>;
  currentAgent: AgentName | null;
  isRunning: boolean;
}

export interface WebSocketEvent {
  event_type:
    | 'AGENT_START'
    | 'AGENT_PROGRESS'
    | 'AGENT_GATE_PASS'
    | 'AGENT_GATE_FAIL'
    | 'AGENT_COMPLETE'
    | 'PIPELINE_COMPLETE'
    | 'PIPELINE_ERROR';
  agent_id: AgentName | null;
  timestamp: number;
  data: Record<string, unknown>;
  message: string;
}

// ─── Resume & Sections ──────────────────────────────────
export interface ResumeHeader {
  name: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin?: string;
  github?: string;
  website?: string;
  photoUrl?: string;
}

export type SectionType = 'summary' | 'experience' | 'skills' | 'education' | 'projects' | 'custom';

export interface ResumeSection {
  id: string;
  type: SectionType;
  title: string;
  position: number;
  content: SummaryContent | ExperienceContent | SkillsContent | EducationContent | ProjectContent;
}

export interface SummaryContent {
  text: string;
}

export interface ExperienceContent {
  entries: ExperienceEntry[];
}

export interface ExperienceEntry {
  company: string;
  title: string;
  startDate: string;
  endDate: string;
  location?: string;
  bullets: Bullet[];
}

export interface SkillsContent {
  categories: SkillCategory[];
}

export interface SkillCategory {
  label: string;
  skills: SkillTag[];
}

export interface SkillTag {
  id: string;
  name: string;
  matched: boolean;
}

export interface EducationContent {
  entries: EducationEntry[];
}

export interface EducationEntry {
  institution: string;
  degree: string;
  field?: string;
  graduationDate: string;
  gpa?: string;
}

export interface ProjectContent {
  entries: ProjectEntry[];
}

export interface ProjectEntry {
  name: string;
  description?: string;
  url?: string;
  bullets: Bullet[];
}

// ─── Bullet ─────────────────────────────────────────────
export type BulletStatus = 'original' | 'user_edited' | 'ai_suggested' | 'accepted' | 'rejected';

export interface Bullet {
  id: string;
  originalText: string;
  currentText: string;
  aiSuggestion: string | null;
  impactScore: number; // 0–1
  status: BulletStatus;
}

// ─── Resume ─────────────────────────────────────────────
export interface Resume {
  id: string;
  header: ResumeHeader;
  sections: ResumeSection[];
  currentVersion: number;
  versions: VersionEntry[];
}

export interface VersionEntry {
  id: string;
  versionNum: number;
  label: string;
  timestamp: string;
  source: 'USER_EDIT' | 'AGENT_OPTIMIZE' | 'USER_ACCEPT' | 'USER_REJECT' | 'SECTION_REORDER';
  agentId?: AgentName;
  scoresAtPoint?: Metrics;
}

// ─── Metrics ────────────────────────────────────────────
export interface Metrics {
  alignment: number;       // 0–1
  keywordCoverage: number; // 0–100
  impactScore: number;     // 0–1
  atsPassRate: number;     // 0–100
  lastUpdated?: string;
  source?: 'AGENT' | 'LOCAL';
}

// ─── Change Data ────────────────────────────────────────
export type ChangeStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED';

export interface ChangeData {
  id: string;
  bulletId: string;
  sectionId: string;
  source: 'USER' | 'AGENT';
  agentId?: AgentName;
  before: string;
  after: string;
  status: ChangeStatus;
  timestamp: string;
}

// ─── JD (Job Description) ──────────────────────────────
export interface ParsedJD {
  id: string;
  rawText: string;
  title: string;
  company: string;
  location?: string;
  keywords: string[];
  requirements: string[];
  responsibilities: string[];
  qualifications: string[];
}

// ─── Keyword Map ────────────────────────────────────────
export interface KeywordItem {
  keyword: string;
  matched: boolean;
  source: 'jd_requirement' | 'skill_match';
}

// ─── Canvas State (API response shape) ─────────────────
export interface CanvasStateResponse {
  resume: Resume;
  metrics: Metrics;
  jd: ParsedJD | null;
  pipeline: PipelineState;
}

// ─── Bullet Scoring Response ────────────────────────────
export interface BulletScoreResponse {
  impactScore: number;
  alignmentDelta: number;
}

export interface BulletSuggestionResponse {
  suggestion: string;
  rationale: string;
}

// ─── Interview Types ────────────────────────────────────
export type InterviewPageState = 'not_generated' | 'generating' | 'ready' | 'practicing';
export type QuestionCategory = 'technical' | 'behavioral' | 'role_specific' | 'company_specific';
export type Difficulty = 'easy' | 'medium' | 'hard';
export type GapType = 'missing_skill' | 'depth_mismatch' | 'missing_domain' | 'recency_gap';
export type GapSeverity = 'high' | 'medium' | 'low';

export interface InterviewData {
  jobId: string;
  resumeId: string;
  jobTitle: string;
  company: string;
  alignmentScore: number;
  gaps: Gap[];
  questions: InterviewQuestion[];
  generatedAt: string;
}

export interface Gap {
  id: string;
  type: GapType;
  description: string;
  jdRequirement: string;
  suggestedTalkingPoint: string;
  severity: GapSeverity;
}

export interface InterviewQuestion {
  id: string;
  text: string;
  category: QuestionCategory;
  difficulty: Difficulty;
  source: 'gap_analysis' | 'resume_jd_alignment' | 'common_for_role';
  whyThisQuestion: string;
  talkingPoints: string[];
  suggestedStructure: string;
}

export interface PracticeFeedback {
  score: number;           // 0–100
  strengths: string[];
  improvements: string[];
  improvedAnswer: string;
}

// ─── API Wrappers ───────────────────────────────────────
export interface ApiResponse<T = unknown> {
  status: 'ok' | 'error';
  data: T;
  meta?: Record<string, unknown>;
}

export interface ApiError {
  status: 'error';
  error: {
    code: string;
    message: string;
  };
}
