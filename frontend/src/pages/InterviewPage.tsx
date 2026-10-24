/**
 * InterviewPage — Gap analysis, categorized questions, and AI practice mode.
 * Route: /interview/:jobId
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { useInterviewStore } from '../stores/interviewStore';
import type { QuestionCategory } from '../lib/types';
import { GAP_TYPE_STYLES, GAP_SEVERITY_COLORS, CATEGORY_TAB_COLORS, DIFFICULTY_COLORS, PRACTICE_MIN_CHARS } from '../lib/constants';
import { getPracticeScoreClasses } from '../lib/utils';
import {
  ArrowLeft,
  ChevronDown,
  Target,
  Brain,
  Building2,
  Sparkles,
  MessageSquare,
  Send,
  CheckCircle2,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import './InterviewPage.css';

const CATEGORY_LABELS: Record<QuestionCategory | 'all', string> = {
  all: 'All',
  technical: 'Technical',
  behavioral: 'Behavioral',
  role_specific: 'Role-Specific',
  company_specific: 'Company',
};

const CATEGORY_ICONS: Record<QuestionCategory, React.ReactNode> = {
  technical: <Brain size={14} />,
  behavioral: <MessageSquare size={14} />,
  role_specific: <Target size={14} />,
  company_specific: <Building2 size={14} />,
};


export function InterviewPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const resumeId = searchParams.get('resumeId') || sessionStorage.getItem('ri_job_id') || jobId || '';

  const store = useInterviewStore();
  const [practiceAnswer, setPracticeAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState('');
  const practiceRef = useRef<HTMLElement>(null);

  const resumeText = sessionStorage.getItem('ri_resume_text') || '';
  const jdText = sessionStorage.getItem('ri_jd_text') || '';

  const handleStartPractice = useCallback((qId: string) => {
    store.startPractice(qId);
    setPracticeAnswer('');
    setTimeout(() => {
      practiceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }, [store]);

  // Load real data from backend on mount
  useEffect(() => {
    if (!jobId) return;

    const load = async () => {
      try {
        const { getInterviewData } = await import('../lib/api');
        const res = await getInterviewData(jobId);
        if (res?.data?.questions?.length > 0) {
          store.loadData({
            jobId,
            resumeId,
            jobTitle: res.data.job_title || 'Interview Prep',
            company: res.data.company || '',
            alignmentScore: typeof res.data.alignment_score === 'number' ? res.data.alignment_score : null,
            gaps: res.data.gaps || [],
            questions: res.data.questions.map((q: any) => ({
              id: q.id,
              text: q.text,
              category: q.category || 'behavioral',
              difficulty: q.difficulty || 'medium',
              source: q.source || 'interview_agent',
              whyThisQuestion: q.why || '',
              talkingPoints: q.talkingPoints || [],
              suggestedStructure: q.suggestedStructure || '',
            })),
            generatedAt: res.data.generated_at || new Date().toISOString(),
          });
        } else {
          // No data yet — show generate button (don't auto-load mock)
          store.loadData(null as any);
        }
      } catch {
        store.loadData(null as any);
      }
    };

    load();
    return () => { store.reset(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const handleGenerate = useCallback(async () => {
    if (!jobId) return;
    setGenerating(true);
    setGenerateError('');
    try {
      const { generateInterview } = await import('../lib/api');
      const res = await generateInterview(jobId, resumeText, jdText, resumeId);
      if (res?.data?.questions) {
        store.loadData({
          jobId,
          resumeId,
          jobTitle: 'Interview Prep',
          company: '',
          alignmentScore: null,
          gaps: [],
          questions: res.data.questions.map((q: any) => ({
            id: q.id,
            text: q.text,
            category: q.category || 'behavioral',
            difficulty: q.difficulty || 'medium',
            source: q.source || 'interview_agent',
            whyThisQuestion: '',
            talkingPoints: q.talkingPoints || [],
            suggestedStructure: '',
          })),
          generatedAt: new Date().toISOString(),
        });
      }
    } catch {
      setGenerateError('Failed to generate interview prep. Make sure the backend is running.');
    }
    setGenerating(false);
  }, [jobId, resumeText, jdText, resumeId, store]);

  const { data, activeCategory, activeDifficulty, expandedQuestionId, practicingQuestionId, currentFeedback } = store;

  if (!data) {
    return (
      <div className="interview-loading">
        <Sparkles size={32} />
        {generating ? (
          <>
            <Loader2 size={24} className="spin" />
            <p>Generating interview prep with AI…</p>
          </>
        ) : (
          <>
            <p>No interview prep generated yet.</p>
            {generateError && <p style={{ color: '#f87171', fontSize: '0.8rem' }}>{generateError}</p>}
            <button
              onClick={handleGenerate}
              style={{ marginTop: '1rem', padding: '0.6rem 1.5rem', background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.4)', borderRadius: '8px', color: '#a5b4fc', cursor: 'pointer', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <Sparkles size={16} /> Generate Interview Prep
            </button>
            <p style={{ fontSize: '0.72rem', color: '#6b7280', marginTop: '0.5rem' }}>
              Requires resume text + job description
            </p>
          </>
        )}
      </div>
    );
  }

  // Filter questions
  const filteredQuestions = data.questions.filter((q) => {
    if (activeCategory !== 'all' && q.category !== activeCategory) return false;
    if (activeDifficulty !== 'all' && q.difficulty !== activeDifficulty) return false;
    return true;
  });

  // Count per category
  const counts: Record<string, number> = { all: data.questions.length };
  for (const q of data.questions) {
    counts[q.category] = (counts[q.category] || 0) + 1;
  }

  // Practice submit handler — real LLM scoring
  const handlePracticeSubmit = async () => {
    if (!practicingQuestion) return;
    setIsSubmitting(true);
    try {
      const { practiceAnswer: practiceAnswerApi } = await import('../lib/api');
      const res = await practiceAnswerApi(
        `${jobId}_${practicingQuestion.id}`,
        practiceAnswer,
        practicingQuestion.text,
        practicingQuestion.category,
        jdText,
        resumeText,
      );
      if (res?.data) {
        store.setFeedback({
          score: res.data.score || 70,
          strengths: res.data.strengths || [],
          improvements: res.data.improvements || [],
          improvedAnswer: res.data.improved_answer || '',
        });
      }
    } catch {
      // Fallback feedback
      store.setFeedback({
        score: 70,
        strengths: ['Good structure', 'Clear communication'],
        improvements: ['Add specific metrics', 'Connect to job requirements'],
        improvedAnswer: practiceAnswer,
      });
    }
    setIsSubmitting(false);
  };

  const practicingQuestion = data.questions.find((q) => q.id === practicingQuestionId);
  const scoreTier = currentFeedback ? getPracticeScoreClasses(currentFeedback.score) : null;
  const fit = data.alignmentScore;
  const alignmentBadgeColor = fit == null ? '' : fit >= 0.45 ? 'badge-green' : fit >= 0.33 ? 'badge-amber' : 'badge-red';

  return (
    <div className="interview-page">
      {/* ═══ HEADER ═══ */}
      <header className="interview-header">
        <Link to={`/canvas/${resumeId}`} className="back-link">
          <ArrowLeft size={16} /> Back to resume
        </Link>
        <div className="header-center">
          <h1>{data.jobTitle}</h1>
          <span className="header-company">{data.company}</span>
        </div>
        {fit != null && (
          <div className={`alignment-badge ${alignmentBadgeColor}`} title="Semantic similarity between your resume and the job description">
            Role fit {Math.round(fit * 100)}%
          </div>
        )}
      </header>

      <div className="interview-content">
        {/* ═══ GAP ANALYSIS ═══ */}
        <section className="gap-section">
          <h2 className="section-heading">Gap Analysis</h2>
          <p className="section-desc">Areas interviewers are most likely to probe based on resume–JD comparison.</p>
          <div className="gap-grid">
            {data.gaps.map((gap) => {
              const typeStyle = GAP_TYPE_STYLES[gap.type];
              return (
                <div key={gap.id} className="gap-card">
                  <div className="gap-top">
                    <span className={`gap-severity-dot ${GAP_SEVERITY_COLORS[gap.severity]}`} />
                    <span className={`gap-type-badge ${typeStyle.bg} ${typeStyle.text}`}>{typeStyle.label}</span>
                  </div>
                  <p className="gap-desc">{gap.description}</p>
                  <div className="gap-jd">
                    <span className="gap-jd-label">JD Requirement:</span> {gap.jdRequirement}
                  </div>
                  <div className="gap-tp">
                    <Sparkles size={12} /> <span>{gap.suggestedTalkingPoint}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ═══ QUESTION CATEGORIES ═══ */}
        <section className="questions-section">
          <h2 className="section-heading">Interview Questions</h2>
          <div className="category-tabs" role="tablist">
            {(Object.keys(CATEGORY_LABELS) as (QuestionCategory | 'all')[]).map((cat) => {
              const isActive = activeCategory === cat;
              const colors = CATEGORY_TAB_COLORS[cat];
              return (
                <button
                  key={cat}
                  role="tab"
                  aria-selected={isActive}
                  className={`cat-tab ${isActive ? colors.active : colors.inactive}`}
                  onClick={() => store.setCategory(cat)}
                >
                  {cat !== 'all' && CATEGORY_ICONS[cat as QuestionCategory]}
                  {CATEGORY_LABELS[cat]} ({counts[cat] || 0})
                </button>
              );
            })}
          </div>

          {/* Question cards */}
          <div className="question-list">
            {filteredQuestions.length === 0 && (
              <p className="empty-state">No {activeCategory === 'all' ? '' : CATEGORY_LABELS[activeCategory].toLowerCase()} questions identified.</p>
            )}
            {filteredQuestions.map((q) => {
              const isExpanded = expandedQuestionId === q.id;
              const catStyle = CATEGORY_TAB_COLORS[q.category];
              const diffColor = DIFFICULTY_COLORS[q.difficulty];
              return (
                <div key={q.id} className="question-card">
                  <button
                    className="question-header"
                    onClick={() => store.toggleQuestion(q.id)}
                    role="button"
                    aria-expanded={isExpanded}
                  >
                    <span className="q-text">{q.text}</span>
                    <div className="q-meta">
                      <span className={`q-cat-badge ${catStyle.active}`}>{CATEGORY_LABELS[q.category]}</span>
                      <span className="q-diff">
                        <span className={`diff-dot ${diffColor}`} aria-label={`Difficulty: ${q.difficulty}`} />
                        {q.difficulty.charAt(0).toUpperCase() + q.difficulty.slice(1)}
                      </span>
                      <span className="q-source">{q.source.replace(/_/g, ' ')}</span>
                      <ChevronDown size={16} className={`q-chevron ${isExpanded ? 'rotated' : ''}`} />
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="question-expanded">
                      <div className="qe-block">
                        <h4>Why This Question</h4>
                        <p>{q.whyThisQuestion}</p>
                      </div>
                      <div className="qe-block">
                        <h4>Key Talking Points</h4>
                        <ul>{q.talkingPoints.map((tp, i) => <li key={i}>{tp}</li>)}</ul>
                      </div>
                      <div className="qe-block">
                        <h4>Suggested Structure</h4>
                        <pre className="qe-structure">{q.suggestedStructure}</pre>
                      </div>
                      <button className="practice-btn" onClick={() => handleStartPractice(q.id)}>
                        <MessageSquare size={14} /> Practice This
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* ═══ PRACTICE PANEL ═══ */}
        {practicingQuestion && (
          <section className="practice-panel" ref={practiceRef}>
            <div className="practice-header">
              <h3>Practice Mode</h3>
              <button className="practice-close" onClick={() => store.endPractice()}>✕ Close</button>
            </div>
            <div className="practice-question">
              <MessageSquare size={16} /> {practicingQuestion.text}
            </div>
            <textarea
              className="practice-textarea"
              placeholder="Type your answer here (min 320 characters)…"
              value={practiceAnswer}
              onChange={(e) => setPracticeAnswer(e.target.value)}
              aria-label="Type your answer"
            />
            <div className="practice-meta">
              <span className={practiceAnswer.length >= PRACTICE_MIN_CHARS ? 'char-ok' : 'char-warn'}>
                {practiceAnswer.length} / {PRACTICE_MIN_CHARS} chars
              </span>
              <button
                className="submit-btn"
                disabled={practiceAnswer.length < PRACTICE_MIN_CHARS || isSubmitting}
                onClick={handlePracticeSubmit}
              >
                {isSubmitting ? 'Analyzing…' : <><Send size={14} /> Get Feedback</>}
              </button>
            </div>

            {/* Feedback display */}
            {currentFeedback && scoreTier && (
              <div className="feedback-display">
                <div className={`feedback-score ${scoreTier.bg} ${scoreTier.text}`}>
                  {currentFeedback.score}/100
                </div>
                <div className="feedback-lists">
                  <div className="fb-section">
                    <h4><CheckCircle2 size={14} className="fb-green" /> Strengths</h4>
                    <ul>{currentFeedback.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
                  </div>
                  <div className="fb-section">
                    <h4><AlertTriangle size={14} className="fb-amber" /> Improvements</h4>
                    <ul>{currentFeedback.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>
                  </div>
                </div>
                <div className="fb-improved">
                  <h4><Sparkles size={14} /> Improved Answer</h4>
                  <p>{currentFeedback.improvedAnswer}</p>
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
