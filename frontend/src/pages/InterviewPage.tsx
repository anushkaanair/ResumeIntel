/**
 * InterviewPage — Gap analysis, categorized questions, and AI practice mode.
 * Route: /interview/:jobId
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { useInterviewStore } from '../stores/interviewStore';
import type { InterviewData, PracticeFeedback, QuestionCategory } from '../lib/types';
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
} from 'lucide-react';
import './InterviewPage.css';

/** Mock interview data for development. */
function createMockInterviewData(jobId: string): InterviewData {
  return {
    jobId,
    resumeId: 'mock-resume',
    jobTitle: 'Senior Full-Stack Engineer',
    company: 'Acme Corp',
    alignmentScore: 0.72,
    gaps: [
      {
        id: 'g1', type: 'missing_skill', severity: 'high',
        description: 'No Kubernetes experience mentioned',
        jdRequirement: 'Kubernetes orchestration at scale',
        suggestedTalkingPoint: 'Discuss Docker expertise and eagerness to expand into K8s. Mention any container orchestration concepts you understand.',
      },
      {
        id: 'g2', type: 'depth_mismatch', severity: 'medium',
        description: 'ML experience appears to be 2 years, JD wants 5+',
        jdRequirement: '5+ years machine learning experience',
        suggestedTalkingPoint: 'Emphasize the breadth and impact of your ML work, even if the duration is shorter. Highlight results over years.',
      },
      {
        id: 'g3', type: 'missing_domain', severity: 'medium',
        description: 'No fintech domain experience visible',
        jdRequirement: 'Experience in financial services or fintech',
        suggestedTalkingPoint: 'Draw parallels between your e-commerce work and fintech: high availability, transaction processing, data security.',
      },
      {
        id: 'g4', type: 'recency_gap', severity: 'low',
        description: 'Last GraphQL mention is 3+ years old',
        jdRequirement: 'Strong GraphQL API design skills',
        suggestedTalkingPoint: 'Mention any recent GraphQL exposure (personal projects, courses) or your ability to ramp up quickly on API technologies.',
      },
    ],
    questions: [
      {
        id: 'q1', text: 'How would you design a scalable microservices architecture for our payment processing platform?',
        category: 'technical', difficulty: 'hard', source: 'resume_jd_alignment',
        whyThisQuestion: 'Your resume highlights microservices experience at TechCorp. The interviewer will want to see if you can apply this to fintech at scale.',
        talkingPoints: ['Discuss event-driven architecture', 'Mention saga pattern for distributed transactions', 'Reference your 15K concurrent requests experience', 'Address fault tolerance and circuit breakers'],
        suggestedStructure: '1. Clarify requirements and scale expectations\n2. Propose high-level architecture\n3. Detail communication patterns\n4. Address data consistency\n5. Discuss monitoring and observability',
      },
      {
        id: 'q2', text: 'Tell me about a time you had to make a difficult technical decision under pressure.',
        category: 'behavioral', difficulty: 'medium', source: 'common_for_role',
        whyThisQuestion: 'Senior roles require decision-making under uncertainty. The interviewer wants to assess your judgment and communication.',
        talkingPoints: ['Use STAR format', 'Choose a decision with real stakes', 'Explain your reasoning process', 'Describe the outcome and what you learned'],
        suggestedStructure: '1. Situation: Set the context\n2. Task: What was at stake\n3. Action: Your decision and rationale\n4. Result: Measurable outcome',
      },
      {
        id: 'q3', text: 'What experience do you have with container orchestration tools like Kubernetes?',
        category: 'technical', difficulty: 'medium', source: 'gap_analysis',
        whyThisQuestion: 'Your resume mentions Docker but not Kubernetes. This is a direct gap probe.',
        talkingPoints: ['Be honest about your K8s exposure level', 'Leverage Docker expertise as a foundation', 'Mention any learning initiatives', 'Discuss container concepts you understand'],
        suggestedStructure: '1. Acknowledge current experience level\n2. Highlight transferable Docker skills\n3. Describe your learning plan\n4. Show enthusiasm for the technology',
      },
      {
        id: 'q4', text: 'How would you approach building a real-time data pipeline for financial transactions?',
        category: 'role_specific', difficulty: 'hard', source: 'resume_jd_alignment',
        whyThisQuestion: 'The role requires building financial data pipelines. They want to test your system design thinking in the fintech domain.',
        talkingPoints: ['Discuss event streaming (Kafka)', 'Address exactly-once semantics', 'Mention compliance and audit trails', 'Reference your database optimization experience'],
        suggestedStructure: '1. Requirements gathering\n2. Data ingestion layer\n3. Processing and transformation\n4. Storage strategy\n5. Monitoring and alerting',
      },
      {
        id: 'q5', text: 'What do you know about Acme Corp and why do you want to work here?',
        category: 'company_specific', difficulty: 'easy', source: 'common_for_role',
        whyThisQuestion: 'Standard company-fit question. Shows you\'ve done research.',
        talkingPoints: ['Research Acme Corp\'s recent news and products', 'Connect their mission to your interests', 'Mention specific technology decisions that excite you'],
        suggestedStructure: '1. Show knowledge of the company\n2. Connect to your experience\n3. Express genuine enthusiasm',
      },
      {
        id: 'q6', text: 'Describe a time you mentored a junior engineer. What was the outcome?',
        category: 'behavioral', difficulty: 'easy', source: 'resume_jd_alignment',
        whyThisQuestion: 'The JD mentions mentoring responsibilities. They want evidence you can lead.',
        talkingPoints: ['Choose a specific mentoring example', 'Describe your approach', 'Show measurable growth in the mentee'],
        suggestedStructure: '1. Context of the mentoring relationship\n2. Your approach and methods\n3. Specific growth metrics\n4. Long-term impact',
      },
      {
        id: 'q7', text: 'How do you handle disagreements about architectural decisions within a team?',
        category: 'behavioral', difficulty: 'medium', source: 'common_for_role',
        whyThisQuestion: 'Senior engineers face architectural debates regularly. They want to see diplomatic technical leadership.',
        talkingPoints: ['Show you value different perspectives', 'Describe using data to resolve debates', 'Mention ADR (Architecture Decision Records)'],
        suggestedStructure: '1. Acknowledge the disagreement\n2. Seek understanding of all positions\n3. Propose evaluation criteria\n4. Drive consensus',
      },
    ],
    generatedAt: new Date().toISOString(),
  };
}

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
  const resumeId = searchParams.get('resumeId') || 'mock-resume';

  const store = useInterviewStore();
  const [practiceAnswer, setPracticeAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const practiceRef = useRef<HTMLElement>(null);

  const handleStartPractice = useCallback((qId: string) => {
    store.startPractice(qId);
    setPracticeAnswer('');
    // Auto-scroll to practice area after React renders it
    setTimeout(() => {
      practiceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }, [store]);

  // Load mock data on mount
  useEffect(() => {
    if (!jobId) return;
    const data = createMockInterviewData(jobId);
    store.loadData(data);
    return () => { store.reset(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const { data, activeCategory, activeDifficulty, expandedQuestionId, practicingQuestionId, currentFeedback } = store;

  if (!data) {
    return (
      <div className="interview-loading">
        <Sparkles size={32} />
        <p>Loading interview prep…</p>
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

  // Practice submit handler
  const handlePracticeSubmit = async () => {
    setIsSubmitting(true);
    // Simulate AI feedback (mock)
    await new Promise((r) => setTimeout(r, 1500));
    const mockFeedback: PracticeFeedback = {
      score: Math.floor(Math.random() * 40) + 55,
      strengths: [
        'Good use of specific examples from your experience',
        'Clear structure in your response',
        'Demonstrated technical depth',
      ],
      improvements: [
        'Include more quantifiable metrics to strengthen your answer',
        'Consider addressing potential follow-up questions proactively',
        'Connect your answer more directly to the company\'s specific needs',
      ],
      improvedAnswer: `${practiceAnswer}\n\nAdditionally, I would emphasize the measurable outcomes: our solution processed 2M+ requests daily with 99.97% uptime, while reducing infrastructure costs by 35%. This directly maps to the scale and reliability requirements in your payment platform.`,
    };
    store.setFeedback(mockFeedback);
    setIsSubmitting(false);
  };

  const practicingQuestion = data.questions.find((q) => q.id === practicingQuestionId);
  const scoreTier = currentFeedback ? getPracticeScoreClasses(currentFeedback.score) : null;
  const alignmentBadgeColor = data.alignmentScore >= 0.75 ? 'badge-green' : data.alignmentScore >= 0.55 ? 'badge-amber' : 'badge-red';

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
        <div className={`alignment-badge ${alignmentBadgeColor}`}>
          {Math.round(data.alignmentScore * 100)}% Aligned
        </div>
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
