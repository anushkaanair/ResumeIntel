/**
 * CanvasPage — Backend-driven resume editing workspace.
 * Loads real pipeline results, shows Original/Optimized toggle,
 * per-bullet AI suggest + edit controls, live ATS score,
 * and GitHub/LinkedIn approval cards.
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  Edit3,
  Check,
  X,
  Download,
  Sparkles,
  Clock,
  Linkedin,
  Github,
  RefreshCw,
  Loader2,
  ToggleLeft,
  ToggleRight,
  AlertTriangle,
  Plus,
  Eye,
  HelpCircle,
  Flag,
} from 'lucide-react';
import {
  getOptimizationResult,
  suggestBullet,
  acceptBullet,
  disputeBullet,
  quickATSScore,
  reoptimizeSection,
  refreshGithub,
  refreshLinkedin,
  regenerateProfileItem,
  getLinkedinAuthUrl,
  getLinkedinStatus,
  exportCanvas,
} from '../lib/api';
import './CanvasPage.css';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ParsedBullet {
  id: string;
  text: string;
  score: number;
  editText: string;
  aiSuggestion: string | null;
  status: 'idle' | 'editing' | 'suggesting' | 'suggested' | 'accepted' | 'rejected';
}

interface ParsedEntry {
  id: string;
  label: string;
  bullets: ParsedBullet[];
  rawText: string;
}

interface ParsedSection {
  id: string;
  title: string;
  entries: ParsedEntry[];
}

interface PipelineMetrics {
  alignment: number;
  keywordCoverage: number;
  impactScore: number;
  atsPassRate: number;
  matchedKeywords?: string[];
  missingKeywords?: string[];
}

interface ProfileItem {
  type: string;
  text: string;
  platform: string;
  url?: string;
  relevance_score?: number;
  decision?: 'added' | 'skipped';
}

interface ProvenanceInfo {
  agent_name: string;
  input_summary: string;
  retrieved_chunk_ids: string[];
  decision_rationale: string;
  confidence: number;
}

// ─── Markdown parser ──────────────────────────────────────────────────────────

function parseMdToSections(md: string): ParsedSection[] {
  const sections: ParsedSection[] = [];
  const sectionBlocks = md.split(/\n(?=## )/);

  for (const block of sectionBlocks) {
    const lines = block.trim().split('\n');
    if (!lines[0]) continue;

    const titleLine = lines[0].replace(/^##\s+/, '').trim();
    if (!titleLine) continue;

    const sectionId = `sec-${titleLine.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}`;
    const section: ParsedSection = { id: sectionId, title: titleLine, entries: [] };

    // Split section body into entries by ### headers
    const body = lines.slice(1).join('\n');
    const entryBlocks = body.split(/\n(?=### )/);

    let entryIdx = 0;
    for (const eb of entryBlocks) {
      const eLines = eb.trim().split('\n');
      if (!eLines[0]) continue;

      const isSubheader = eLines[0].startsWith('### ');
      const entryLabel = isSubheader ? eLines[0].replace(/^###\s+/, '').trim() : '';
      const contentLines = isSubheader ? eLines.slice(1) : eLines;

      const bullets: ParsedBullet[] = [];
      const textLines: string[] = [];

      for (const line of contentLines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
          const bulletText = trimmed.replace(/^[-•*]\s+/, '').trim();
          if (bulletText) {
            const bId = `b-${sectionId}-${entryIdx}-${bullets.length}`;
            bullets.push({
              id: bId,
              text: bulletText,
              score: scoreBulletLocally(bulletText),
              editText: bulletText,
              aiSuggestion: null,
              status: 'idle',
            });
          }
        } else if (!trimmed.startsWith('#')) {
          textLines.push(trimmed);
        }
      }

      const entryId = `entry-${sectionId}-${entryIdx}`;
      section.entries.push({
        id: entryId,
        label: entryLabel,
        bullets,
        rawText: textLines.join('\n'),
      });
      entryIdx++;
    }

    // If no sub-entries were found but there's raw content, create one entry
    if (section.entries.length === 0) {
      const allBullets: ParsedBullet[] = [];
      const allText: string[] = [];
      for (const line of lines.slice(1)) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
          const bulletText = trimmed.replace(/^[-•*]\s+/, '').trim();
          if (bulletText) {
            const bId = `b-${sectionId}-0-${allBullets.length}`;
            allBullets.push({
              id: bId,
              text: bulletText,
              score: scoreBulletLocally(bulletText),
              editText: bulletText,
              aiSuggestion: null,
              status: 'idle',
            });
          }
        } else {
          allText.push(trimmed);
        }
      }
      if (allBullets.length > 0 || allText.length > 0) {
        section.entries.push({ id: `entry-${sectionId}-0`, label: '', bullets: allBullets, rawText: allText.join('\n') });
      }
    }

    sections.push(section);
  }

  return sections;
}

const STRONG_VERBS = ['led', 'designed', 'implemented', 'optimized', 'delivered', 'built', 'architected', 'automated', 'reduced', 'increased', 'achieved', 'launched', 'deployed', 'engineered'];

function scoreBulletLocally(text: string): number {
  const lower = text.toLowerCase();
  const hasVerb = STRONG_VERBS.some(v => lower.startsWith(v));
  const hasMetric = /\d/.test(text);
  const hasOutcome = /%|revenue|users|latency|uptime|saving|reduced|improved/.test(lower);
  return Math.min(0.3 + (hasVerb ? 0.25 : 0) + (hasMetric ? 0.25 : 0) + (hasOutcome ? 0.2 : 0), 1.0);
}

function sectionsToText(sections: ParsedSection[]): string {
  return sections.map(sec => {
    const entriesText = sec.entries.map(e => {
      const hdr = e.label ? `### ${e.label}\n` : '';
      const raw = e.rawText ? e.rawText + '\n' : '';
      const bullets = e.bullets.map(b => `- ${b.text}`).join('\n');
      return hdr + raw + bullets;
    }).join('\n\n');
    return `## ${sec.title}\n${entriesText}`;
  }).join('\n\n');
}

function getScoreColor(v: number): string {
  if (v >= 0.8) return 'score-green';
  if (v >= 0.6) return 'score-amber';
  return 'score-red';
}

// ─── Bullet component ─────────────────────────────────────────────────────────

interface BulletCardProps {
  bullet: ParsedBullet;
  jdText: string;
  resumeText: string;
  provenance: ProvenanceInfo | null;
  onUpdate: (bulletId: string, patch: Partial<ParsedBullet>) => void;
  onATSRecalc: () => void;
}

function BulletCard({ bullet, jdText, resumeText, provenance, onUpdate, onATSRecalc }: BulletCardProps) {
  const [localEdit, setLocalEdit] = useState(bullet.editText);
  const [whyOpen, setWhyOpen] = useState(false);
  const [disputeText, setDisputeText] = useState('');
  const [disputing, setDisputing] = useState(false);
  const [disputeResult, setDisputeResult] = useState<string | null>(null);

  const handleEdit = () => {
    setLocalEdit(bullet.text);
    onUpdate(bullet.id, { status: 'editing', editText: bullet.text });
  };

  const handleEditSave = () => {
    if (!localEdit.trim()) return;
    onUpdate(bullet.id, { text: localEdit.trim(), editText: localEdit.trim(), status: 'idle' });
    onATSRecalc();
  };

  const handleEditCancel = () => {
    onUpdate(bullet.id, { status: 'idle', editText: bullet.text });
  };

  const handleAISuggest = async () => {
    onUpdate(bullet.id, { status: 'suggesting' });
    try {
      const res = await suggestBullet(bullet.id, bullet.text, jdText, resumeText);
      const suggestion = res?.data?.suggestion || '';
      onUpdate(bullet.id, { status: 'suggested', aiSuggestion: suggestion });
    } catch {
      onUpdate(bullet.id, { status: 'idle' });
    }
  };

  const handleAccept = async () => {
    const newText = bullet.aiSuggestion || bullet.text;
    onUpdate(bullet.id, { text: newText, editText: newText, status: 'accepted', aiSuggestion: null });
    onATSRecalc();
    try { await acceptBullet(bullet.id, 'ai', newText); } catch { /* best effort */ }
  };

  const handleReject = () => {
    onUpdate(bullet.id, { status: 'idle', aiSuggestion: null });
  };

  const handleDisputeSubmit = async () => {
    if (!disputeText.trim()) return;
    setDisputing(true);
    setDisputeResult(null);
    try {
      const res = await disputeBullet(bullet.id, bullet.text, disputeText.trim(), jdText, resumeText);
      const newScore = res?.data?.revised_score;
      const revisedBullet = res?.data?.revised_bullet;
      const rationale = res?.data?.provenance?.decision_rationale || 'Re-evaluation complete.';
      setDisputeResult(rationale);
      const patch: Partial<ParsedBullet> = {};
      if (typeof newScore === 'number') patch.score = newScore;
      if (revisedBullet && revisedBullet !== bullet.text) patch.aiSuggestion = revisedBullet;
      if (Object.keys(patch).length > 0) onUpdate(bullet.id, patch);
    } catch {
      setDisputeResult('Could not reach the re-evaluation service. Please try again.');
    }
    setDisputing(false);
  };

  const scoreColor = getScoreColor(bullet.score);
  const isAccepted = bullet.status === 'accepted';

  return (
    <li className={`bullet-item ${bullet.aiSuggestion ? 'has-suggestion' : ''} ${isAccepted ? 'bullet-accepted' : ''}`}>
      <div className="bullet-row">
        {bullet.status === 'editing' ? (
          <div className="bullet-edit-area">
            <textarea
              className="bullet-textarea"
              value={localEdit}
              onChange={e => setLocalEdit(e.target.value)}
              rows={3}
              autoFocus
            />
            <div className="bullet-edit-actions">
              <button className="ai-accept" onClick={handleEditSave}><Check size={13} /> Save</button>
              <button className="ai-reject" onClick={handleEditCancel}><X size={13} /> Cancel</button>
            </div>
          </div>
        ) : (
          <>
            <span className={`bullet-text ${isAccepted ? 'bullet-text-accepted' : ''}`}>{bullet.text}</span>
            <span className={`impact-badge ${scoreColor}`}>{bullet.score.toFixed(2)}</span>
            <button className="bullet-edit-btn" title="Edit" onClick={handleEdit}><Edit3 size={13} /></button>
            <button
              className="bullet-ai-btn"
              title="AI Suggest"
              onClick={handleAISuggest}
              disabled={bullet.status === 'suggesting'}
            >
              {bullet.status === 'suggesting' ? <Loader2 size={13} className="spin" /> : <Sparkles size={13} />}
            </button>
            <button
              className="bullet-why-btn"
              title="Why this score?"
              onClick={() => setWhyOpen(o => !o)}
            >
              <HelpCircle size={13} />
            </button>
          </>
        )}
      </div>

      {bullet.aiSuggestion && bullet.status === 'suggested' && (
        <div className="ai-suggestion-box">
          <div className="ai-suggestion-label"><Sparkles size={11} /> AI Suggestion</div>
          <p className="ai-text">{bullet.aiSuggestion}</p>
          <div className="ai-actions">
            <button className="ai-accept" onClick={handleAccept}><Check size={13} /> Accept</button>
            <button className="ai-reject" onClick={handleReject}><X size={13} /> Dismiss</button>
          </div>
        </div>
      )}

      {whyOpen && (
        <div className="why-panel">
          <div className="why-header">
            <HelpCircle size={12} />
            <strong>Why this content?</strong>
            <button className="approval-close" onClick={() => setWhyOpen(false)}><X size={13} /></button>
          </div>

          {provenance ? (
            <div className="why-body">
              <div className="why-row"><span className="why-label">Agent</span><span>{provenance.agent_name}</span></div>
              <div className="why-row"><span className="why-label">Confidence</span><span className={getScoreColor(provenance.confidence)}>{(provenance.confidence * 100).toFixed(0)}%</span></div>
              <div className="why-row"><span className="why-label">Sources used</span><span>{provenance.retrieved_chunk_ids.length} retrieved segment(s)</span></div>
              <p className="why-rationale">{provenance.decision_rationale}</p>
            </div>
          ) : (
            <p className="why-rationale">No provenance trail recorded for this bullet yet.</p>
          )}

          <div className="dispute-area">
            <label className="why-label" htmlFor={`dispute-${bullet.id}`}><Flag size={11} /> Disagree with this? Tell us why</label>
            <textarea
              id={`dispute-${bullet.id}`}
              className="bullet-textarea dispute-textarea"
              value={disputeText}
              onChange={e => setDisputeText(e.target.value)}
              rows={2}
              placeholder="e.g. this metric understates the real impact..."
            />
            <button className="ai-accept dispute-submit" onClick={handleDisputeSubmit} disabled={disputing || !disputeText.trim()}>
              {disputing ? <Loader2 size={13} className="spin" /> : <Flag size={13} />} Submit Dispute
            </button>
            {disputeResult && <p className="dispute-result">{disputeResult}</p>}
          </div>
        </div>
      )}
    </li>
  );
}

// ─── Profile approval card ────────────────────────────────────────────────────

interface ProfileApprovalPanelProps {
  items: ProfileItem[];
  platform: string;
  onAdd: (item: ProfileItem) => void;
  onSkip: (item: ProfileItem) => void;
  onDone: () => void;
}

function ProfileApprovalPanel({ items, platform, onAdd, onSkip, onDone }: ProfileApprovalPanelProps) {
  const pending = items.filter(i => !i.decision);
  if (pending.length === 0) {
    return (
      <div className="profile-approval-panel">
        <div className="approval-done">
          <Check size={20} /> All {platform} updates reviewed!
          <button className="ai-accept" onClick={onDone}>Done</button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-approval-panel">
      <div className="approval-header">
        {platform === 'github' ? <Github size={16} /> : <Linkedin size={16} />}
        <strong>{pending.length} new {platform} update{pending.length > 1 ? 's' : ''} — add to resume?</strong>
        <button className="approval-close" onClick={onDone}><X size={14} /></button>
      </div>
      <div className="approval-items">
        {pending.map((item, idx) => (
          <div key={idx} className="approval-card">
            <div className="approval-text">
              <span className="approval-type-badge">{item.type}</span>
              {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.text}</a> : <span>{item.text}</span>}
              {item.relevance_score !== undefined && (
                <span className="approval-relevance">{Math.round(item.relevance_score * 100)}% relevant</span>
              )}
            </div>
            <div className="approval-actions">
              <button className="ai-accept" onClick={() => onAdd(item)}><Plus size={13} /> Add</button>
              <button className="ai-reject" onClick={() => onSkip(item)}><X size={13} /> Skip</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function CanvasPage() {
  const { resumeId } = useParams<{ resumeId: string }>();

  // Session data (set by OptimizePage)
  const originalResumeText = sessionStorage.getItem('ri_resume_text') || '';
  const jdText = sessionStorage.getItem('ri_jd_text') || '';
  const resumeFilename = sessionStorage.getItem('ri_resume_filename') || 'resume';

  // Core state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'optimized' | 'original'>('optimized');
  const [sections, setSections] = useState<ParsedSection[]>([]);
  const [metrics, setMetrics] = useState<PipelineMetrics | null>(null);
  const [tailoringProvenance, setTailoringProvenance] = useState<ProvenanceInfo | null>(null);
  const [liveATS, setLiveATS] = useState<number | null>(null);
  const [atsRecalculating, setATSRecalculating] = useState(false);
  const [jdOpen, setJdOpen] = useState(true);
  const [reoptimizingSection, setReoptimizingSection] = useState<string | null>(null);

  // Profile sync state
  const [githubItems, setGithubItems] = useState<ProfileItem[]>([]);
  const [linkedinItems, setLinkedinItems] = useState<ProfileItem[]>([]);
  const [showGithubApproval, setShowGithubApproval] = useState(false);
  const [showLinkedinApproval, setShowLinkedinApproval] = useState(false);
  const [githubRefreshing, setGithubRefreshing] = useState(false);
  const [linkedinRefreshing, setLinkedinRefreshing] = useState(false);
  const [linkedinConnected, setLinkedinConnected] = useState(false);
  const [streamingAgent, setStreamingAgent] = useState<string | null>(null);
  const [pipelinePending, setPipelinePending] = useState(false);

  // ATS debounce
  const atsDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Load pipeline result ──────────────────────────────────────────────────
  useEffect(() => {
    if (!resumeId) return;

    const load = async () => {
      setLoading(true);
      try {
        // If ID starts with "local-", use local parsing (no backend call)
        if (resumeId.startsWith('local-')) {
          const parsed = parseMdToSections(originalResumeText || '# Resume\nNo content available.');
          setSections(parsed);
          setLoading(false);
          return;
        }

        const res = await getOptimizationResult(resumeId);
        if (res?.data?.status === 'completed' || res?.data?.optimized_content) {
          const optimizedContent = res.data.optimized_content || res.data.agents?.tailoring?.content || '';
          const parsed = parseMdToSections(optimizedContent);
          setSections(parsed);
          if (res.data.metrics) {
            setMetrics(res.data.metrics);
            setLiveATS(res.data.metrics.atsPassRate);
          }
          if (res.data.agents?.tailoring?.provenance) {
            setTailoringProvenance(res.data.agents.tailoring.provenance);
          }
        } else {
          // Pipeline still running — render the original text now and let the
          // WebSocket effect below stream in partial agent results as they
          // complete (patent claim 12), rather than blocking on full completion.
          const parsed = parseMdToSections(originalResumeText || '');
          setSections(parsed);
          setPipelinePending(true);
        }
      } catch {
        // Fallback: parse original resume text if backend not available
        const parsed = parseMdToSections(originalResumeText || '');
        setSections(parsed);
      }
      setLoading(false);
    };

    load();
  }, [resumeId]);

  // ── WebSocket partial-result streaming (patent claim 12) ─────────────────
  // Renders each agent's output into the canvas as soon as it completes,
  // instead of waiting for the full pipeline to finish.
  useEffect(() => {
    if (!resumeId || !pipelinePending || resumeId.startsWith('local-')) return;

    const wsBase = ((import.meta as any).env.VITE_API_URL || 'http://localhost:8000/api/v1')
      .replace(/^http/, 'ws')
      .replace(/\/api\/v1\/?$/, '');
    const ws = new WebSocket(`${wsBase}/ws/optimize/${resumeId}`);

    ws.onmessage = (evt) => {
      try {
        const event = JSON.parse(evt.data);
        if (event.event_type === 'AGENT_START') {
          setStreamingAgent(event.agent_name || null);
        } else if (event.event_type === 'AGENT_COMPLETE') {
          setStreamingAgent(null);
          const content = event.data?.content;
          if (content) {
            const parsed = parseMdToSections(content);
            if (parsed.length > 0) setSections(parsed);
          }
          if (event.agent_name === 'Tailoring' && event.data?.provenance) {
            setTailoringProvenance(event.data.provenance);
          }
        } else if (event.event_type === 'PIPELINE_COMPLETE' || event.event_type === 'ALIGNMENT_GATE_ABORT') {
          setStreamingAgent(null);
          setPipelinePending(false);
          getOptimizationResult(resumeId).then(res => {
            if (res?.data?.metrics) {
              setMetrics(res.data.metrics);
              setLiveATS(res.data.metrics.atsPassRate);
            }
            if (res?.data?.agents?.tailoring?.provenance) {
              setTailoringProvenance(res.data.agents.tailoring.provenance);
            }
            const finalContent = res?.data?.optimized_content || res?.data?.agents?.tailoring?.content;
            if (finalContent) {
              const parsed = parseMdToSections(finalContent);
              if (parsed.length > 0) setSections(parsed);
            }
          }).catch(() => { /* best effort */ });
          ws.close();
        }
      } catch { /* ignore malformed frames */ }
    };

    ws.onerror = () => setPipelinePending(false);

    return () => ws.close();
  }, [resumeId, pipelinePending]);

  // ── LinkedIn OAuth callback handling + connection status ─────────────────
  useEffect(() => {
    if (!resumeId) return;

    const params = new URLSearchParams(window.location.search);
    const linkedinParam = params.get('linkedin');
    if (linkedinParam === 'connected') {
      setLinkedinConnected(true);
      window.history.replaceState({}, '', window.location.pathname);
    } else if (linkedinParam === 'error') {
      alert('LinkedIn connection failed. Please try again.');
      window.history.replaceState({}, '', window.location.pathname);
    } else {
      getLinkedinStatus(resumeId)
        .then(res => setLinkedinConnected(!!res?.data?.connected))
        .catch(() => { /* best effort */ });
    }
  }, [resumeId]);

  // ── Connect LinkedIn (kicks off OAuth redirect) ───────────────────────────
  const handleLinkedinConnect = useCallback(async () => {
    if (!resumeId) return;
    try {
      const res = await getLinkedinAuthUrl(resumeId);
      if (res?.data?.auth_url) {
        window.location.href = res.data.auth_url;
      }
    } catch {
      alert('LinkedIn OAuth is not configured. Set LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET in .env.');
    }
  }, [resumeId]);

  // ── Update a bullet ───────────────────────────────────────────────────────
  const updateBullet = useCallback((bulletId: string, patch: Partial<ParsedBullet>) => {
    setSections(prev => prev.map(sec => ({
      ...sec,
      entries: sec.entries.map(entry => ({
        ...entry,
        bullets: entry.bullets.map(b => b.id === bulletId ? { ...b, ...patch } : b),
      })),
    })));
  }, []);

  // ── ATS live recalculation ────────────────────────────────────────────────
  const triggerATSRecalc = useCallback(() => {
    if (atsDebounceRef.current) clearTimeout(atsDebounceRef.current);
    atsDebounceRef.current = setTimeout(async () => {
      const currentText = sectionsToText(sections);
      if (!currentText.trim()) return;
      setATSRecalculating(true);
      try {
        const res = await quickATSScore(currentText, jdText);
        if (res?.data?.ats_score !== undefined) {
          setLiveATS(res.data.ats_score);
        }
      } catch { /* best effort */ }
      setATSRecalculating(false);
    }, 800);
  }, [sections, jdText]);

  // ── Section reoptimize ────────────────────────────────────────────────────
  const handleReoptimizeSection = useCallback(async (sectionId: string, sectionTitle: string) => {
    setReoptimizingSection(sectionId);
    try {
      const sectionContent = sections.find(s => s.id === sectionId);
      const content = sectionContent ? sectionsToText([sectionContent]) : '';
      const res = await reoptimizeSection(sectionId, sectionTitle, content, jdText, originalResumeText);
      if (res?.data?.content) {
        const newSection = parseMdToSections(res.data.content);
        if (newSection.length > 0) {
          setSections(prev => prev.map(s => s.id === sectionId ? { ...newSection[0], id: sectionId } : s));
          triggerATSRecalc();
        }
      }
    } catch { /* best effort */ }
    setReoptimizingSection(null);
  }, [sections, jdText, originalResumeText, triggerATSRecalc]);

  // ── GitHub refresh ────────────────────────────────────────────────────────
  const handleGithubRefresh = useCallback(async () => {
    setGithubRefreshing(true);
    try {
      const res = await refreshGithub(jdText);
      const items: ProfileItem[] = res?.data?.items || [];
      if (items.length > 0) {
        setGithubItems(items);
        setShowGithubApproval(true);
      } else {
        alert('No new GitHub updates found relevant to this job description.');
      }
    } catch {
      alert('Could not fetch GitHub data. Please set GITHUB_ACCESS_TOKEN in your .env file.');
    }
    setGithubRefreshing(false);
  }, [jdText]);

  // ── LinkedIn refresh ──────────────────────────────────────────────────────
  const handleLinkedinRefresh = useCallback(async () => {
    if (!resumeId) return;
    setLinkedinRefreshing(true);
    try {
      const res = await refreshLinkedin(jdText, '', resumeId);
      if (res?.data?.connected === false) {
        setLinkedinConnected(false);
        if (window.confirm('LinkedIn is not connected yet. Connect now?')) {
          await handleLinkedinConnect();
        }
      } else {
        setLinkedinConnected(true);
        const items: ProfileItem[] = res?.data?.items || [];
        if (items.length > 0) {
          setLinkedinItems(items);
          setShowLinkedinApproval(true);
        } else {
          alert('No new LinkedIn updates found relevant to this job description.');
        }
      }
    } catch {
      alert('Could not fetch LinkedIn data.');
    }
    setLinkedinRefreshing(false);
  }, [jdText, resumeId, handleLinkedinConnect]);

  // ── Add profile item to resume ────────────────────────────────────────────
  const addProfileItem = useCallback(async (item: ProfileItem, platform: string) => {
    // Route the approved delta through Generation + Quality before insertion
    // (patent claim 1d — no raw platform text is inserted verbatim).
    let textToInsert = item.text;
    try {
      const res = await regenerateProfileItem(item.text, platform as 'github' | 'linkedin', jdText, originalResumeText);
      if (res?.data?.text) {
        textToInsert = res.data.text;
      }
    } catch { /* fall back to raw text if regeneration fails */ }

    setSections(prev => {
      const skillsSec = prev.find(s => s.title.toLowerCase().includes('skill') || s.title.toLowerCase().includes('project'));
      if (!skillsSec) {
        // Append to last section
        const last = prev[prev.length - 1];
        if (!last) return prev;
        const newBullet: ParsedBullet = {
          id: `b-added-${Date.now()}`,
          text: textToInsert,
          score: scoreBulletLocally(textToInsert),
          editText: textToInsert,
          aiSuggestion: null,
          status: 'accepted',
        };
        return prev.map(s => s.id === last.id ? {
          ...s,
          entries: [...s.entries, { id: `entry-added-${Date.now()}`, label: `From ${platform}`, bullets: [newBullet], rawText: '' }],
        } : s);
      }
      const newBullet: ParsedBullet = {
        id: `b-added-${Date.now()}`,
        text: textToInsert,
        score: scoreBulletLocally(textToInsert),
        editText: textToInsert,
        aiSuggestion: null,
        status: 'accepted',
      };
      return prev.map(s => s.id === skillsSec.id ? {
        ...s,
        entries: s.entries.map((e, i) => i === 0 ? { ...e, bullets: [...e.bullets, newBullet] } : e),
      } : s);
    });

    // Mark as added
    if (platform === 'github') {
      setGithubItems(prev => prev.map(i => i === item ? { ...i, decision: 'added' } : i));
    } else {
      setLinkedinItems(prev => prev.map(i => i === item ? { ...i, decision: 'added' } : i));
    }
    triggerATSRecalc();
  }, [triggerATSRecalc, jdText, originalResumeText]);

  // ── Export ────────────────────────────────────────────────────────────────
  const handleExport = useCallback(async (format: 'docx' | 'pdf' = 'docx') => {
    const sectionData = sections.map(sec => ({
      title: sec.title,
      content: {
        entries: sec.entries.map(e => ({
          company: e.label,
          bullets: e.bullets.map(b => ({
            currentText: b.text,
            originalText: b.text,
            status: b.status === 'accepted' ? 'accepted' : 'user_modified',
          })),
        })),
        text: sec.entries.map(e => e.rawText).filter(Boolean).join('\n'),
      },
    }));

    try {
      const resp = await exportCanvas(resumeId || 'resume', sectionData, format);
      const blob = new Blob([resp.data], {
        type: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${resumeFilename}_optimized.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Export failed. Make sure the backend is running.');
    }
  }, [sections, resumeId, resumeFilename]);

  // ── Loading / error states ────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="canvas-loading">
        <Loader2 size={36} className="spin" />
        <p>Loading optimization results…</p>
      </div>
    );
  }

  // ── ATS score display ─────────────────────────────────────────────────────
  const displayATS = liveATS ?? metrics?.atsPassRate ?? 0;
  const atsColor = displayATS >= 85 ? 'score-green' : displayATS >= 65 ? 'score-amber' : 'score-red';
  const atsLabel = displayATS >= 85 ? 'ATS Ready ✓' : displayATS >= 65 ? 'Needs Improvement' : 'Needs Work';

  const jdKeywords = jdText
    ? Array.from(new Set(jdText.toLowerCase().match(/\b[a-zA-Z]{3,}\b/g) || [])).slice(0, 20)
    : [];

  return (
    <div className="canvas-page">
      {/* ── Left: JD Panel ──────────────────────────────────────────────── */}
      <aside className={`jd-panel ${jdOpen ? 'jd-open' : 'jd-closed'}`}>
        <button className="jd-toggle" onClick={() => setJdOpen(!jdOpen)} aria-label={jdOpen ? 'Collapse' : 'Expand'}>
          {jdOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
        </button>
        {jdOpen && (
          <div className="jd-content">
            <h3 className="jd-title">Job Description</h3>
            {jdText ? (
              <>
                <div className="jd-section">
                  <p className="jd-text">{jdText.slice(0, 600)}{jdText.length > 600 ? '…' : ''}</p>
                </div>
                {jdKeywords.length > 0 && (
                  <div className="jd-section">
                    <h4 className="jd-section-title">Keywords</h4>
                    <div className="jd-keywords">
                      {jdKeywords.map(kw => (
                        <span key={kw} className="keyword-tag">{kw}</span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="jd-text jd-empty">No job description provided.</p>
            )}
          </div>
        )}
      </aside>

      {/* ── Center: Resume canvas ────────────────────────────────────────── */}
      <main className="canvas-center">
        {/* Top bar */}
        <div className="canvas-topbar">
          <Link to="/optimize" className="back-link">
            <ChevronLeft size={16} /> New Optimization
          </Link>

          {streamingAgent && (
            <span className="streaming-badge" title="Live pipeline streaming">
              <Loader2 size={12} className="spin" /> {streamingAgent} running…
            </span>
          )}

          {/* Original / Optimized toggle */}
          <div className="view-toggle">
            <button
              className={`toggle-btn ${view === 'original' ? 'toggle-active' : ''}`}
              onClick={() => setView('original')}
            >
              <Eye size={14} /> Original
            </button>
            <button
              className={`toggle-btn ${view === 'optimized' ? 'toggle-active' : ''}`}
              onClick={() => setView('optimized')}
            >
              {view === 'optimized' ? <ToggleRight size={14} /> : <ToggleLeft size={14} />} Optimized
            </button>
          </div>

          {/* Profile sync buttons */}
          <div className="profile-sync-btns">
            <button className="sync-btn" onClick={handleGithubRefresh} disabled={githubRefreshing} title="Refresh GitHub">
              {githubRefreshing ? <Loader2 size={14} className="spin" /> : <Github size={14} />}
            </button>
            <button
              className={`sync-btn ${linkedinConnected ? 'sync-btn-connected' : ''}`}
              onClick={linkedinConnected ? handleLinkedinRefresh : handleLinkedinConnect}
              disabled={linkedinRefreshing}
              title={linkedinConnected ? 'Refresh LinkedIn' : 'Connect LinkedIn'}
            >
              {linkedinRefreshing ? <Loader2 size={14} className="spin" /> : <Linkedin size={14} />}
            </button>
            <button className="sync-btn" onClick={handleGithubRefresh} title="Refresh">
              <RefreshCw size={14} />
            </button>
          </div>

          <div className="canvas-topbar-actions">
            <button className="export-btn" onClick={() => handleExport('docx')}>
              <Download size={14} /> Export DOCX
            </button>
            <button className="export-btn export-btn-secondary" onClick={() => handleExport('pdf')}>
              <Download size={14} /> PDF
            </button>
          </div>
        </div>

        {/* Profile approval panels */}
        {showGithubApproval && (
          <ProfileApprovalPanel
            items={githubItems}
            platform="github"
            onAdd={item => addProfileItem(item, 'github')}
            onSkip={item => setGithubItems(prev => prev.map(i => i === item ? { ...i, decision: 'skipped' } : i))}
            onDone={() => setShowGithubApproval(false)}
          />
        )}
        {showLinkedinApproval && (
          <ProfileApprovalPanel
            items={linkedinItems}
            platform="linkedin"
            onAdd={item => addProfileItem(item, 'linkedin')}
            onSkip={item => setLinkedinItems(prev => prev.map(i => i === item ? { ...i, decision: 'skipped' } : i))}
            onDone={() => setShowLinkedinApproval(false)}
          />
        )}

        {/* ATS Score Banner */}
        <div className={`ats-banner ${atsColor}`}>
          <div className="ats-banner-left">
            <span className="ats-label">ATS Score</span>
            <span className="ats-score-value">{displayATS.toFixed(1)}%</span>
            {atsRecalculating && <Loader2 size={12} className="spin ats-spin" />}
            <span className={`ats-status-label ${atsColor}`}>{atsLabel}</span>
          </div>
          {displayATS < 85 && (
            <div className="ats-banner-right">
              <AlertTriangle size={13} />
              <span>Mandatory target: 85%+ — accept AI suggestions to improve</span>
            </div>
          )}
          <div className="ats-bar-track">
            <div className={`ats-bar-fill ${atsColor}`} style={{ width: `${Math.min(displayATS, 100)}%` }} />
            <div className="ats-bar-target" style={{ left: '85%' }} title="85% target" />
          </div>
        </div>

        {/* Resume content */}
        <div className="resume-document">
          {view === 'original' ? (
            <div className="original-view">
              <div className="original-badge"><Eye size={12} /> Original Resume</div>
              <pre className="original-text">{originalResumeText || 'No original resume text available.'}</pre>
            </div>
          ) : (
            <>
              {error && (
                <div className="canvas-error-banner">
                  <AlertTriangle size={14} /> {error}
                </div>
              )}
              {sections.length === 0 ? (
                <div className="canvas-empty">
                  <p>No optimized content yet. Start an optimization first.</p>
                  <Link to="/optimize" className="ai-accept">Start Optimization</Link>
                </div>
              ) : (
                sections.map(section => (
                  <div key={section.id} className="resume-section" data-section-type={section.title.toLowerCase()}>
                    <div className="section-header">
                      <h2 className="section-title">{section.title}</h2>
                      <div className="section-controls">
                        <button
                          className="section-reoptimize-btn"
                          onClick={() => handleReoptimizeSection(section.id, section.title)}
                          disabled={reoptimizingSection === section.id}
                          title="Re-optimize section with AI"
                        >
                          {reoptimizingSection === section.id
                            ? <Loader2 size={13} className="spin" />
                            : <Sparkles size={13} />}
                          <span>AI Reoptimize</span>
                        </button>
                      </div>
                    </div>

                    {section.entries.map(entry => (
                      <div key={entry.id} className="entry-block">
                        {entry.label && (
                          <div className="entry-header">
                            {entry.label.split('|').map((part, i) => (
                              <span key={i} className={i === 0 ? 'entry-company' : i === 1 ? 'entry-title' : 'entry-date'}>
                                {part.trim()}
                              </span>
                            ))}
                          </div>
                        )}
                        {entry.rawText && !entry.bullets.length && (
                          <p className="entry-raw-text">{entry.rawText}</p>
                        )}
                        {entry.rawText && entry.bullets.length > 0 && (
                          <p className="entry-raw-text">{entry.rawText}</p>
                        )}
                        {entry.bullets.length > 0 && (
                          <ul className="bullet-list">
                            {entry.bullets.map(bullet => (
                              <BulletCard
                                key={bullet.id}
                                bullet={bullet}
                                jdText={jdText}
                                resumeText={originalResumeText}
                                provenance={tailoringProvenance}
                                onUpdate={updateBullet}
                                onATSRecalc={triggerATSRecalc}
                              />
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                ))
              )}
            </>
          )}
        </div>

        {/* Interview prep link */}
        <div className="canvas-footer">
          <Link
            to={`/interview/${resumeId}?resumeId=${resumeId}`}
            className="interview-link"
          >
            <Clock size={14} /> Prepare for Interview
          </Link>
        </div>
      </main>

      {/* ── Right: Metrics sidebar ───────────────────────────────────────── */}
      <aside className="metrics-sidebar">
        <h3 className="sidebar-title">Metrics</h3>

        {/* Live ATS score — prominent */}
        <div className={`ats-score-card ${atsColor}`}>
          <div className="ats-score-label">ATS Score</div>
          <div className="ats-score-big">{displayATS.toFixed(1)}%</div>
          {atsRecalculating && <div className="ats-recalc-badge"><Loader2 size={10} className="spin" /> Recalculating…</div>}
          <div className="ats-score-target">Target: 85%+</div>
          <div className="metric-bar-bg-sm">
            <div className={`metric-bar-fill-sm ${atsColor}`} style={{ width: `${Math.min(displayATS, 100)}%` }} />
          </div>
        </div>

        {metrics && (
          <div className="metrics-grid">
            {[
              { label: 'Alignment', value: metrics.alignment, pct: `${Math.round(metrics.alignment * 100)}%` },
              { label: 'Keywords', value: metrics.keywordCoverage / 100, pct: `${metrics.keywordCoverage}%` },
              { label: 'Impact', value: metrics.impactScore, pct: `${Math.round(metrics.impactScore * 100)}%` },
            ].map(m => (
              <div key={m.label} className="metric-card-sm">
                <div className="metric-label-sm">{m.label}</div>
                <div className={`metric-value-sm ${getScoreColor(m.value)}`}>{m.pct}</div>
                <div className="metric-bar-bg-sm">
                  <div className={`metric-bar-fill-sm ${getScoreColor(m.value)}`} style={{ width: `${m.value * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Missing keywords */}
        {metrics?.missingKeywords && metrics.missingKeywords.length > 0 && (
          <div className="sidebar-section">
            <h4 className="sidebar-section-title">Missing Keywords</h4>
            <div className="missing-keywords">
              {metrics.missingKeywords.slice(0, 10).map(kw => (
                <span key={kw} className="keyword-tag keyword-missing">{kw}</span>
              ))}
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="sidebar-section">
          <h4 className="sidebar-section-title">Score Guide</h4>
          <div className="legend">
            <span className="legend-dot score-green" /> Good (0.8+)
            <span className="legend-dot score-yellow" /> Moderate (0.6–0.8)
            <span className="legend-dot score-red" /> Needs Work (&lt;0.6)
          </div>
        </div>

        <div className="sidebar-actions">
          <button className="sidebar-action-btn" onClick={() => handleExport('docx')}>
            <Download size={14} /> Download DOCX
          </button>
          <button className="sidebar-action-btn sidebar-action-secondary" onClick={() => handleExport('pdf')}>
            <Download size={14} /> Download PDF
          </button>
        </div>
      </aside>
    </div>
  );
}
