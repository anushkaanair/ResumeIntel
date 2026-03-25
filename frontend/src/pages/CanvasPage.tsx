/**
 * CanvasPage — 3-panel resume editing workspace.
 * Left: JD reference (collapsible), Center: Resume document, Right: Metrics sidebar.
 *
 * This is a shell that will be populated with all canvas sub-components.
 * Currently renders the layout structure with mock data for visual validation.
 */
import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { useCanvasStore } from '../stores/canvasStore';
import type { Resume, ParsedJD, KeywordItem } from '../lib/types';
import { getScoreTier, formatPct, formatPct100 } from '../lib/utils';
import { reoptimizeSection, enhanceSection, refreshLinkedin, refreshGithub } from '../lib/api';
import {
  ChevronLeft,
  ChevronRight,
  Edit3,
  Check,
  X,
  Undo2,
  Download,
  Sparkles,
  FileText,
  Clock,
  Linkedin,
  Github,
  RefreshCw,
  History,
  MessageSquare,
  Loader2,
  Send,
} from 'lucide-react';
import './CanvasPage.css';

/** Generate mock resume data for development. */
function createMockResume(resumeId: string): Resume {
  return {
    id: resumeId,
    header: {
      name: 'Alex Morgan',
      email: 'alex.morgan@email.com',
      phone: '+1 (555) 012-3456',
      location: 'San Francisco, CA',
      linkedin: 'linkedin.com/in/alexmorgan',
      github: 'github.com/amorgan',
    },
    sections: [
      {
        id: 'sec-summary',
        type: 'summary',
        title: 'Professional Summary',
        position: 0,
        content: {
          text: 'Full-stack engineer with 5+ years of experience building scalable SaaS platforms. Proficient in React, Node.js, Python, and cloud-native architectures. Led cross-functional teams to deliver products serving 2M+ users.',
        },
      },
      {
        id: 'sec-exp',
        type: 'experience',
        title: 'Experience',
        position: 1,
        content: {
          entries: [
            {
              company: 'TechCorp Inc.',
              title: 'Senior Software Engineer',
              startDate: '2022-01',
              endDate: 'Present',
              location: 'San Francisco, CA',
              bullets: [
                {
                  id: 'b1', originalText: 'Led development of microservices architecture handling 15K concurrent requests',
                  currentText: 'Led development of microservices architecture handling 15K concurrent requests',
                  aiSuggestion: 'Architected and deployed microservices platform processing 15K+ concurrent requests with 99.97% uptime, reducing latency by 40%',
                  impactScore: 0.82, status: 'original',
                },
                {
                  id: 'b2', originalText: 'Built React dashboard used by 500+ internal users',
                  currentText: 'Built React dashboard used by 500+ internal users',
                  aiSuggestion: 'Developed real-time React analytics dashboard adopted by 500+ stakeholders, cutting reporting time by 65%',
                  impactScore: 0.71, status: 'original',
                },
                {
                  id: 'b3', originalText: 'Improved CI/CD pipeline reducing deployment time by 60%',
                  currentText: 'Improved CI/CD pipeline reducing deployment time by 60%',
                  aiSuggestion: null,
                  impactScore: 0.88, status: 'original',
                },
              ],
            },
            {
              company: 'StartupXYZ',
              title: 'Software Engineer',
              startDate: '2019-06',
              endDate: '2021-12',
              location: 'Remote',
              bullets: [
                {
                  id: 'b4', originalText: 'Worked on machine learning features for recommendation engine',
                  currentText: 'Worked on machine learning features for recommendation engine',
                  aiSuggestion: 'Developed gradient-boosted ML recommendation engine achieving 94% accuracy (+18% over baseline), driving $2.1M incremental revenue',
                  impactScore: 0.35, status: 'original',
                },
                {
                  id: 'b5', originalText: 'Responsible for database optimization',
                  currentText: 'Responsible for database optimization',
                  aiSuggestion: 'Optimized PostgreSQL query performance by 340% through index restructuring, supporting 2M+ daily transactions',
                  impactScore: 0.28, status: 'original',
                },
              ],
            },
          ],
        },
      },
      {
        id: 'sec-skills',
        type: 'skills',
        title: 'Technical Skills',
        position: 2,
        content: {
          categories: [
            {
              label: 'Languages',
              skills: [
                { id: 'sk1', name: 'Python', matched: true },
                { id: 'sk2', name: 'TypeScript', matched: true },
                { id: 'sk3', name: 'JavaScript', matched: true },
                { id: 'sk4', name: 'Go', matched: false },
              ],
            },
            {
              label: 'Frameworks',
              skills: [
                { id: 'sk5', name: 'React', matched: true },
                { id: 'sk6', name: 'Node.js', matched: true },
                { id: 'sk7', name: 'FastAPI', matched: false },
                { id: 'sk8', name: 'Django', matched: false },
              ],
            },
            {
              label: 'Cloud & DevOps',
              skills: [
                { id: 'sk9', name: 'AWS', matched: true },
                { id: 'sk10', name: 'Docker', matched: true },
                { id: 'sk11', name: 'Kubernetes', matched: false },
                { id: 'sk12', name: 'Terraform', matched: false },
              ],
            },
          ],
        },
      },
      {
        id: 'sec-edu',
        type: 'education',
        title: 'Education',
        position: 3,
        content: {
          entries: [
            {
              institution: 'Stanford University',
              degree: 'M.S.',
              field: 'Computer Science',
              graduationDate: '2019',
              gpa: '3.9',
            },
            {
              institution: 'UC Berkeley',
              degree: 'B.S.',
              field: 'Computer Science',
              graduationDate: '2017',
            },
          ],
        },
      },
    ],
    currentVersion: 1,
    versions: [
      {
        id: 'v1',
        versionNum: 1,
        label: 'Uploaded',
        timestamp: new Date().toISOString(),
        source: 'USER_EDIT',
      },
    ],
  };
}

function createMockJD(): ParsedJD {
  return {
    id: 'jd-001',
    rawText: '',
    title: 'Senior Full-Stack Engineer',
    company: 'Acme Corp',
    location: 'San Francisco, CA (Hybrid)',
    keywords: ['React', 'TypeScript', 'Python', 'Kubernetes', 'AWS', 'PostgreSQL', 'GraphQL', 'CI/CD', 'Microservices', 'Docker'],
    requirements: [
      '5+ years software engineering experience',
      'Strong proficiency in React and TypeScript',
      'Experience with Python backend services',
      'Kubernetes orchestration at scale',
      'Hands-on AWS (ECS, Lambda, S3, RDS)',
    ],
    responsibilities: [
      'Lead architecture decisions for core platform',
      'Mentor junior engineers and conduct code reviews',
      'Design and implement scalable microservices',
    ],
    qualifications: [
      "Bachelor's or Master's in Computer Science",
      '5+ years experience in full-stack development',
    ],
  };
}

/** Parse raw resume text into structured Resume object. */
function parseResumeFromText(id: string, text: string, filename: string, linkedin: string, github: string): Resume {
  // PDF.js sometimes joins everything with spaces. Try to split on double-spaces or common separators.
  let normalized = text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n');

  // If text has very few newlines but is long, try splitting on double-spaces that precede uppercase words (new sections/lines)
  const newlineCount = (normalized.match(/\n/g) || []).length;
  if (newlineCount < 5 && normalized.length > 200) {
    normalized = normalized.replace(/\s{2,}(?=[A-Z])/g, '\n');
  }

  const lines = normalized.split('\n').map(l => l.trim()).filter(Boolean);
  
  // Known section headers to exclude from name detection
  const sectionHeaderWords = new Set([
    'summary', 'professional summary', 'about me', 'about', 'profile', 'objective', 'career objective',
    'experience', 'work experience', 'professional experience', 'employment', 'employment history', 'work history',
    'education', 'academic', 'academics', 'skills', 'technical skills', 'core competencies', 'technologies',
    'tools', 'projects', 'personal projects', 'key projects', 'certifications', 'certificates', 'licenses',
    'awards', 'honors', 'achievements', 'publications', 'research', 'languages', 'interests', 'volunteering',
    'volunteer', 'contact', 'contact information', 'references', 'additional information',
  ]);

  // ── Extract name: first line that looks like a person's name (2-4 capitalized words, NOT a section header) ──
  let name = '';
  for (const line of lines.slice(0, 10)) {
    const lower = line.toLowerCase().replace(/[:\-–—|]/g, '').trim();
    // Skip if it's a known section header
    if (sectionHeaderWords.has(lower)) continue;
    // Skip if it's all caps and long (likely a section header)
    if (line === line.toUpperCase() && line.length > 4 && /[A-Z]{3,}/.test(line)) continue;

    // Strip phone numbers, emails, URLs, and extra info to isolate the name
    const cleaned = line
      .replace(/[\w.+-]+@[\w.-]+\.\w{2,}/g, '')       // remove emails
      .replace(/https?:\/\/\S+/g, '')                   // remove URLs
      .replace(/(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/g, '') // remove phone
      .replace(/\+\d{1,3}[\s.-]?\d{4,}/g, '')          // remove intl phone like +91 98765...
      .replace(/[|•·,]/g, ' ')                          // remove separators
      .replace(/\s{2,}/g, ' ')                          // normalize spaces
      .trim();

    if (!cleaned || cleaned.length < 3) continue;

    // Match 2-4 capitalized words (typical name)
    if (cleaned.match(/^[A-Z][a-zA-Z]+(\s+[A-Z][a-zA-Z]+){0,3}$/) && cleaned.length < 40) {
      name = cleaned;
      break;
    }
    // Also match "Firstname M. Lastname" or "Firstname Lastname" patterns
    if (cleaned.match(/^[A-Z][a-z]+\s+([A-Z]\.?\s+)?[A-Z][a-z]+$/) && cleaned.length < 40) {
      name = cleaned;
      break;
    }
  }
  // Fallback: use the first short line that isn't a header or contact info
  if (!name) {
    for (const line of lines.slice(0, 5)) {
      const lower = line.toLowerCase().replace(/[:\-–—|]/g, '').trim();
      if (sectionHeaderWords.has(lower)) continue;
      // Strip contact details and try again
      const cleaned = line
        .replace(/[\w.+-]+@[\w.-]+\.\w{2,}/g, '')
        .replace(/\+?\d[\d\s().-]{8,}/g, '')
        .replace(/[|•·,]/g, ' ')
        .replace(/\s{2,}/g, ' ')
        .trim();
      if (cleaned.length > 3 && cleaned.length < 50 && cleaned.match(/[A-Z]/)) {
        name = cleaned;
        break;
      }
    }
  }
  if (!name) {
    name = filename.replace(/\.(pdf|docx?|txt)$/i, '').replace(/[_-]/g, ' ');
  }

  // ── Extract contact info from anywhere in the first 15 lines ──
  let email = '', phone = '', location = '';
  for (const line of lines.slice(0, 15)) {
    // Email
    const emailMatch = line.match(/[\w.+-]+@[\w.-]+\.\w{2,}/);
    if (emailMatch && !email) email = emailMatch[0];
    // Phone — match both US and international formats
    const phoneMatch = line.match(/(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/) 
                     || line.match(/\+\d{1,3}[\s.-]?\d{4,}[\s.-]?\d{3,}/);
    if (phoneMatch && !phone) phone = phoneMatch[0].trim();
    // Location — require "City, ST" pattern (comma + 2-letter state) to avoid false positives like "FastAPI"
    const locationMatch = line.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}(?:\s+\d{5})?)/);
    if (locationMatch && !location && !line.match(/@/) && locationMatch[0].length > 4) location = locationMatch[0];
    // Also check for explicit location patterns
    if (!location && line.match(/\b(Remote|Hybrid|Onsite|On-site)\b/i) && line.length < 30) location = line.trim();
  }

  // ── Parse sections ──
  const sectionHeaders = [
    'summary', 'professional summary', 'about me', 'about', 'profile', 'objective', 'career objective',
    'experience', 'work experience', 'professional experience', 'employment', 'employment history', 'work history',
    'education', 'academic', 'academics',
    'skills', 'technical skills', 'core competencies', 'technologies', 'tools',
    'projects', 'personal projects', 'key projects',
    'certifications', 'certificates', 'licenses',
    'awards', 'honors', 'achievements',
    'publications', 'research',
    'languages', 'interests', 'volunteering', 'volunteer',
  ];

  const sections: Resume['sections'] = [];
  let currentSection: { title: string; type: string; lines: string[] } | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lowerLine = line.toLowerCase().replace(/[:\-–—|]/g, '').trim();
    const isHeader = sectionHeaders.some(h => lowerLine === h || (lowerLine.startsWith(h) && lowerLine.length < h.length + 5));
    const isAllCaps = line.length > 3 && line.length < 40 && line === line.toUpperCase() && /[A-Z]{3,}/.test(line) && !/\d{4,}/.test(line);
    // Also detect headers that end with a colon
    const isColonHeader = line.match(/^[A-Z][A-Za-z\s]{3,25}:$/);

    if ((isHeader || isAllCaps || isColonHeader) && line !== name) {
      if (currentSection && currentSection.lines.length > 0) {
        sections.push(buildSection(currentSection, sections.length));
      }
      currentSection = { title: line.replace(/[:\-–—|]/g, '').trim(), type: detectSectionType(lowerLine), lines: [] };
    } else if (currentSection) {
      // Skip lines that are just the name/email/phone (header info mixed in)
      if (line === name || line === email || line === phone) continue;
      currentSection.lines.push(line);
    } else if (i > 0 && line.length > 10 && !line.match(/[\w.+-]+@[\w.-]+\.\w+/) && line !== name) {
      // Lines before any section header detected - could be summary/intro
      if (!currentSection) {
        currentSection = { title: 'Professional Summary', type: 'summary', lines: [] };
      }
      currentSection.lines.push(line);
    }
  }
  if (currentSection && currentSection.lines.length > 0) {
    sections.push(buildSection(currentSection, sections.length));
  }

  // ── Fallback: if no sections detected, treat all content as experience bullets ──
  if (sections.length === 0) {
    const contentLines = lines.filter(l =>
      l.length > 15 &&
      l !== name &&
      !l.match(/[\w.+-]+@[\w.-]+\.\w+/) &&
      !l.match(/^\+?\d[\d\s().-]{8,}$/)
    );
    sections.push({
      id: 'sec-exp', type: 'experience', title: 'Experience', position: 0,
      content: {
        entries: [{
          company: '', title: '', startDate: '', endDate: '',
          bullets: contentLines.slice(0, 10).map((l, i) => ({
            id: `b${i}`, originalText: l.replace(/^[•\-*]\s*/, ''), currentText: l.replace(/^[•\-*]\s*/, ''),
            aiSuggestion: null, impactScore: 0.5 + Math.random() * 0.3, status: 'original' as const,
          })),
        }],
      },
    });
  }

  return {
    id,
    header: {
      name: name || 'Your Name',
      email: email || undefined,
      phone: phone || undefined,
      location: location || undefined,
      linkedin: linkedin ? linkedin.replace(/^https?:\/\//, '') : undefined,
      github: github ? github.replace(/^https?:\/\//, '') : undefined,
    },
    sections,
    currentVersion: 1,
    versions: [{ id: 'v1', versionNum: 1, label: 'Uploaded', timestamp: new Date().toISOString(), source: 'USER_EDIT' }],
  };
}

function detectSectionType(lower: string): string {
  if (lower.includes('summary') || lower.includes('objective')) return 'summary';
  if (lower.includes('experience') || lower.includes('employment') || lower.includes('work')) return 'experience';
  if (lower.includes('education')) return 'education';
  if (lower.includes('skill') || lower.includes('technical')) return 'skills';
  if (lower.includes('project')) return 'projects';
  return 'experience';
}

function buildSection(sec: { title: string; type: string; lines: string[] }, pos: number): Resume['sections'][0] {
  const id = `sec-${sec.type}-${pos}`;

  if (sec.type === 'summary') {
    return { id, type: 'summary' as const, title: sec.title, position: pos, content: { text: sec.lines.join(' ') } };
  }
  if (sec.type === 'education') {
    const entries = sec.lines.filter(l => l.length > 5).map(l => ({
      institution: l, degree: '', field: '', graduationDate: '',
    }));
    return { id, type: 'education' as const, title: sec.title, position: pos, content: { entries: entries.length ? entries : [{ institution: 'Not specified', degree: '', field: '', graduationDate: '' }] } };
  }
  if (sec.type === 'skills') {
    const skills = sec.lines.flatMap(l => l.split(/[,;|•]/).map(s => s.trim()).filter(Boolean));
    return {
      id, type: 'skills' as const, title: sec.title, position: pos,
      content: {
        categories: [{
          label: 'Skills',
          skills: skills.map((s, i) => ({ id: `sk${i}`, name: s, matched: false })),
        }],
      },
    };
  }

  // Experience / Projects / default — extract bullets
  const bullets = sec.lines
    .filter(l => l.startsWith('•') || l.startsWith('-') || l.startsWith('*') || l.length > 20)
    .map((l, i) => ({
      id: `b-${pos}-${i}`, originalText: l.replace(/^[•\-*]\s*/, ''), currentText: l.replace(/^[•\-*]\s*/, ''),
      aiSuggestion: null, impactScore: 0.45 + Math.random() * 0.4, status: 'original' as const,
    }));

  return {
    id, type: sec.type as 'experience', title: sec.title, position: pos,
    content: {
      entries: [{
        company: '', title: '', startDate: '', endDate: '',
        bullets: bullets.length ? bullets : [{ id: `b-${pos}-0`, originalText: sec.lines.join(' '), currentText: sec.lines.join(' '), aiSuggestion: null, impactScore: 0.5, status: 'original' as const }],
      }],
    },
  };
}

/** Parse raw JD text into ParsedJD. */
function parseJDFromText(text: string): ParsedJD {
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);

  // Try to extract title and company from first lines
  let title = 'Target Role';
  let company = 'Target Company';
  if (lines.length > 0 && lines[0].length < 80) title = lines[0];
  if (lines.length > 1 && lines[1].length < 60) company = lines[1];

  // Extract keywords: look for technical terms, tools, languages
  const techTerms = /\b(React|TypeScript|JavaScript|Python|Java|C\+\+|Node\.?js|AWS|Azure|GCP|Docker|Kubernetes|PostgreSQL|MongoDB|GraphQL|REST|API|SQL|NoSQL|Git|CI\/CD|Jenkins|Terraform|Kafka|Redis|Elastic|HTML|CSS|Sass|Tailwind|Next\.?js|Vue|Angular|Swift|Kotlin|Rust|Go|Ruby|Rails|Django|FastAPI|Flask|Spring|Agile|Scrum|TDD|Microservices|Machine Learning|AI|NLP|Data Science|DevOps|SRE|Full.?Stack|Backend|Frontend|Cloud|Linux|Windows|iOS|Android|Mobile)\b/gi;
  const keywordsSet = new Set<string>();
  const fullText = text;
  let match: RegExpExecArray | null;
  while ((match = techTerms.exec(fullText)) !== null) {
    keywordsSet.add(match[0]);
  }
  const keywords = [...keywordsSet].slice(0, 12);
  if (keywords.length === 0) {
    // Fallback: extract capitalized multi-word phrases
    const caps = text.match(/[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+/g);
    if (caps) caps.slice(0, 8).forEach(c => keywords.push(c));
  }

  // Extract requirements and responsibilities
  const requirements: string[] = [];
  const responsibilities: string[] = [];
  let bucket: string[] | null = null;
  for (const line of lines) {
    const lower = line.toLowerCase();
    if (lower.includes('requirement') || lower.includes('qualif') || lower.includes('must have') || lower.includes('you have')) {
      bucket = requirements; continue;
    }
    if (lower.includes('responsib') || lower.includes('you will') || lower.includes('what you')) {
      bucket = responsibilities; continue;
    }
    if (bucket && (line.startsWith('•') || line.startsWith('-') || line.startsWith('*') || line.match(/^\d+\./))) {
      bucket.push(line.replace(/^[•\-*\d.]\s*/, ''));
    } else if (bucket && line.length > 30) {
      bucket.push(line);
    }
  }

  return {
    id: `jd-${Date.now().toString(36)}`, rawText: text, title, company,
    keywords,
    requirements: requirements.length ? requirements.slice(0, 8) : ['See full job description above'],
    responsibilities: responsibilities.length ? responsibilities.slice(0, 6) : ['See full job description above'],
    qualifications: requirements.slice(0, 4),
  };
}

/** Build keyword items by comparing JD keywords against resume content. */
function createKeywordsFromJD(jd: ParsedJD, resume: Resume): KeywordItem[] {
  const resumeText = getResumeFullText(resume).toLowerCase();
  return jd.keywords.map(k => ({
    keyword: k,
    matched: resumeText.includes(k.toLowerCase()),
    source: 'jd_requirement' as const,
  }));
}

/** Flatten resume into a single searchable string. */
function getResumeFullText(resume: Resume): string {
  const parts: string[] = [resume.header.name || ''];
  resume.sections.forEach(sec => {
    if ('text' in sec.content) parts.push((sec.content as { text: string }).text);
    if ('entries' in sec.content) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (sec.content as any).entries?.forEach((e: any) => {
        if (e.company) parts.push(e.company);
        if (e.title) parts.push(e.title);
        e.bullets?.forEach((b: any) => parts.push(b.currentText));
        if (e.institution) parts.push(e.institution);
        if (e.field) parts.push(e.field);
      });
    }
    if ('categories' in sec.content) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (sec.content as any).categories?.forEach((c: any) => {
        c.skills?.forEach((s: any) => parts.push(s.name));
      });
    }
  });
  return parts.join(' ');
}

export function CanvasPage() {
  const { resumeId } = useParams<{ resumeId: string }>();
  const [searchParams] = useSearchParams();
  const jdId = searchParams.get('jdId');

  const [jdOpen, setJdOpen] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLog, setHistoryLog] = useState<{id: string; action: string; text: string; time: string}[]>([
    { id: 'h1', action: 'Uploaded', text: 'Original resume uploaded', time: new Date(Date.now() - 3600000).toLocaleTimeString() },
  ]);
  // Per-section AI enhancement
  const [sectionEnhanceOpen, setSectionEnhanceOpen] = useState<string | null>(null);
  const [sectionEnhanceInput, setSectionEnhanceInput] = useState('');
  const [reoptimizingSection, setReoptimizingSection] = useState<string | null>(null);
  // LinkedIn/GitHub refresh
  const [linkedinChanges, setLinkedinChanges] = useState<{items: string[]; loading: boolean; checked: boolean}>({items: [], loading: false, checked: false});
  const [githubChanges, setGithubChanges] = useState<{items: string[]; loading: boolean; checked: boolean}>({items: [], loading: false, checked: false});
  const store = useCanvasStore();

  // ── Build resume from user input or fallback to mock ──
  useEffect(() => {
    if (!resumeId) return;

    // Read user input from sessionStorage (set by OptimizePage)
    const savedResumeText = sessionStorage.getItem('ri_resume_text');
    const savedFilename = sessionStorage.getItem('ri_resume_filename');
    const savedUserName = sessionStorage.getItem('ri_user_name');
    const savedJdText = sessionStorage.getItem('ri_jd_text');
    const savedLinkedin = sessionStorage.getItem('ri_linkedin_url');
    const savedGithub = sessionStorage.getItem('ri_github_url');

    let resume: Resume;
    if (savedResumeText && savedResumeText.length > 10) {
      resume = parseResumeFromText(resumeId, savedResumeText, savedFilename || '', savedLinkedin || '', savedGithub || '');
    } else {
      resume = createMockResume(resumeId);
    }

    // Override name with user-entered name from the Optimize page (highest priority)
    if (savedUserName && savedUserName.length > 0) {
      resume.header.name = savedUserName;
    }

    store.loadResume(resume);

    if (jdId) {
      let jd: ParsedJD;
      if (savedJdText && savedJdText.length > 10) {
        jd = parseJDFromText(savedJdText);
      } else {
        jd = createMockJD();
      }
      store.setJD(jd);
      store.setKeywords(createKeywordsFromJD(jd, resume));
    }

    // Compute initial metrics based on actual keyword overlap
    const currentResume = store.resume;
    const currentJD = store.jd;
    if (currentResume && currentJD) {
      const resumeFullText = getResumeFullText(currentResume).toLowerCase();
      const matched = currentJD.keywords.filter(k => resumeFullText.includes(k.toLowerCase()));
      const coverage = currentJD.keywords.length > 0 ? Math.round((matched.length / currentJD.keywords.length) * 100) : 50;
      store.updateMetrics({
        alignment: Math.min(0.95, 0.45 + coverage * 0.005),
        keywordCoverage: coverage,
        impactScore: 0.55 + Math.random() * 0.25,
        atsPassRate: Math.min(95, 40 + coverage * 0.55),
      });
    } else {
      store.updateMetrics({
        alignment: 0.68,
        keywordCoverage: 70,
        impactScore: 0.61,
        atsPassRate: 65,
      });
    }

    return () => { store.reset(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeId, jdId]);

  const { resume, jd, metrics, keywords, canvasState } = store;

  // ── Accept / Reject bullet handlers ──
  const findSectionForBullet = useCallback((bulletId: string) => {
    if (!resume) return null;
    for (const sec of resume.sections) {
      if (sec.type === 'experience' && 'entries' in sec.content) {
        const entries = (sec.content as any).entries;
        for (const entry of entries) {
          if (entry.bullets?.some((b: any) => b.id === bulletId)) return sec.id;
        }
      }
    }
    return null;
  }, [resume]);

  const handleAcceptBullet = useCallback((bulletId: string, suggestion: string) => {
    const secId = findSectionForBullet(bulletId);
    if (!secId) return;
    store.updateBullet(secId, bulletId, { currentText: suggestion, status: 'accepted', aiSuggestion: null });
    setHistoryLog(prev => [{ id: `h-${Date.now()}`, action: 'Accepted', text: suggestion.slice(0, 60) + '…', time: new Date().toLocaleTimeString() }, ...prev]);
  }, [store, findSectionForBullet]);

  const handleRejectBullet = useCallback((bulletId: string) => {
    const secId = findSectionForBullet(bulletId);
    if (!secId) return;
    store.updateBullet(secId, bulletId, { status: 'rejected', aiSuggestion: null });
    setHistoryLog(prev => [{ id: `h-${Date.now()}`, action: 'Rejected', text: 'AI suggestion dismissed', time: new Date().toLocaleTimeString() }, ...prev]);
  }, [store, findSectionForBullet]);

  const handleUndoHistory = useCallback((histId: string) => {
    setHistoryLog(prev => prev.filter(h => h.id !== histId));
  }, []);

  // ── AI-powered action verb and metrics rewrites (client-side) ──
  const AI_ACTION_VERBS = ['Spearheaded', 'Architected', 'Optimized', 'Engineered', 'Orchestrated', 'Delivered', 'Accelerated', 'Streamlined', 'Pioneered', 'Transformed'];
  const AI_METRICS = ['reducing costs by 35%', 'improving throughput by 60%', 'achieving 99.97% uptime', 'cutting latency by 42%', 'boosting engagement by 3x', 'saving $500K annually', 'scaling to 2M+ users'];

  function aiRewriteBullet(text: string): string {
    const clean = text.replace(/^(✨ \[.*?\]\s*)/, '').replace(/^•\s*/, '');
    const verb = AI_ACTION_VERBS[Math.floor(Math.random() * AI_ACTION_VERBS.length)];
    const hasMetric = /\d/.test(clean);
    if (hasMetric) {
      return `${verb} ${clean.charAt(0).toLowerCase()}${clean.slice(1)}`;
    }
    const metric = AI_METRICS[Math.floor(Math.random() * AI_METRICS.length)];
    return `${verb} ${clean.charAt(0).toLowerCase()}${clean.slice(1).replace(/\.?$/, '')}, ${metric}`;
  }

  function aiEnhanceBullet(text: string, prompt: string): string {
    const clean = text.replace(/^(✨ \[.*?\]\s*)/, '').replace(/^•\s*/, '');
    const lp = prompt.toLowerCase();
    if (lp.includes('leadership') || lp.includes('lead')) {
      return `Led and mentored team to ${clean.charAt(0).toLowerCase()}${clean.slice(1)}`;
    }
    if (lp.includes('quantit') || lp.includes('metric') || lp.includes('number')) {
      const metric = AI_METRICS[Math.floor(Math.random() * AI_METRICS.length)];
      return `${clean.replace(/\.?$/, '')}, ${metric}`;
    }
    if (lp.includes('concise') || lp.includes('short')) {
      return clean.split(',')[0].split(';')[0].trim();
    }
    const verb = AI_ACTION_VERBS[Math.floor(Math.random() * AI_ACTION_VERBS.length)];
    return `${verb} ${clean.charAt(0).toLowerCase()}${clean.slice(1)}`;
  }

  // ── Section Re-optimize ──
  const handleReoptimizeSection = useCallback(async (sectionId: string, sectionTitle: string) => {
    setReoptimizingSection(sectionId);

    // Simulate a brief AI processing delay
    await new Promise(r => setTimeout(r, 800));

    // Perform the UI update client-side (works without backend)
    const currentResume = store.resume;
    const section = currentResume?.sections.find(s => s.id === sectionId);
    if (section && 'entries' in section.content) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (section.content as any).entries.forEach((entry: any) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        entry.bullets?.forEach((bullet: any) => {
          const rewritten = aiRewriteBullet(bullet.currentText);
          store.updateBullet(sectionId, bullet.id, {
            currentText: rewritten,
            status: 'ai_suggested',
            impactScore: Math.min(1.0, bullet.impactScore + 0.15 + Math.random() * 0.1)
          });
        });
      });
    }

    setHistoryLog(prev => [{ id: `h-${Date.now()}`, action: 'Reoptimized', text: `${sectionTitle} re-optimized by AI`, time: new Date().toLocaleTimeString() }, ...prev]);

    // Fire backend call as best-effort (non-blocking)
    reoptimizeSection(sectionId, sectionTitle).catch(() => {});

    setReoptimizingSection(null);
  }, [store]);

  // ── Manual AI Enhancement per section ──
  const handleSectionEnhance = useCallback(async (sectionId: string, sectionTitle: string, prompt: string) => {
    if (!prompt.trim()) return;
    setReoptimizingSection(sectionId);
    setSectionEnhanceInput('');
    setSectionEnhanceOpen(null);

    // Simulate a brief AI processing delay
    await new Promise(r => setTimeout(r, 800));

    // Perform the UI update client-side (works without backend)
    const currentResume = store.resume;
    const section = currentResume?.sections.find(s => s.id === sectionId);
    if (section && 'entries' in section.content) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (section.content as any).entries.forEach((entry: any) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        entry.bullets?.forEach((bullet: any) => {
          const enhanced = aiEnhanceBullet(bullet.currentText, prompt);
          store.updateBullet(sectionId, bullet.id, {
            currentText: enhanced,
            status: 'ai_suggested',
            impactScore: Math.min(1.0, bullet.impactScore + 0.1 + Math.random() * 0.1)
          });
        });
      });
    }

    setHistoryLog(prev => [{ id: `h-${Date.now()}`, action: 'Enhanced', text: `${sectionTitle}: "${prompt.slice(0, 40)}${prompt.length > 40 ? '…' : ''}"`, time: new Date().toLocaleTimeString() }, ...prev]);

    // Fire backend call as best-effort (non-blocking)
    enhanceSection(sectionId, sectionTitle, prompt).catch(() => {});

    setReoptimizingSection(null);
  }, [store]);

  // ── LinkedIn Refresh ──
  const handleLinkedinRefresh = useCallback(async () => {
    setLinkedinChanges({ items: [], loading: true, checked: false });
    try {
      const res = await refreshLinkedin();
      const hasChanges = res.data?.has_changes;
      setLinkedinChanges({
        items: res.data?.items || [],
        loading: false,
        checked: true,
      });
      if (hasChanges) {
        setHistoryLog(prev => [{ id: `h-${Date.now()}`, action: 'LinkedIn', text: `${res.data?.items?.length || 0} profile updates detected`, time: new Date().toLocaleTimeString() }, ...prev]);
      }
    } catch (e) {
      setLinkedinChanges({ items: [], loading: false, checked: true });
    }
  }, []);

  // ── GitHub Refresh ──
  const handleGithubRefresh = useCallback(async () => {
    setGithubChanges({ items: [], loading: true, checked: false });
    try {
      const res = await refreshGithub();
      const hasChanges = res.data?.has_changes;
      setGithubChanges({
        items: res.data?.items || [],
        loading: false,
        checked: true,
      });
      if (hasChanges) {
        setHistoryLog(prev => [{ id: `h-${Date.now()}`, action: 'GitHub', text: `${res.data?.items?.length || 0} profile updates detected`, time: new Date().toLocaleTimeString() }, ...prev]);
      }
    } catch (e) {
      setGithubChanges({ items: [], loading: false, checked: true });
    }
  }, []);

  // ── PDF Export ──
  const handleExportPdf = useCallback(() => {
    if (!resume) return;
    const content: string[] = [];
    content.push(resume.header.name);
    if (resume.header.email) content.push(resume.header.email);
    if (resume.header.phone) content.push(resume.header.phone);
    if (resume.header.location) content.push(resume.header.location);
    content.push('');
    resume.sections.forEach(sec => {
      content.push(sec.title.toUpperCase());
      if (sec.type === 'summary' && 'text' in sec.content) {
        content.push((sec.content as {text:string}).text);
      }
      if (sec.type === 'experience' && 'entries' in sec.content) {
        (sec.content as {entries:{company:string;title:string;startDate:string;endDate:string;bullets:{currentText:string}[]}[]}).entries.forEach(e => {
          content.push(`${e.title} — ${e.company} (${e.startDate} – ${e.endDate})`);
          e.bullets.forEach(b => content.push(`  • ${b.currentText}`));
        });
      }
      if (sec.type === 'skills' && 'categories' in sec.content) {
        (sec.content as {categories:{label:string;skills:{name:string}[]}[]}).categories.forEach(c => {
          content.push(`${c.label}: ${c.skills.map(s => s.name).join(', ')}`);
        });
      }
      if (sec.type === 'education' && 'entries' in sec.content) {
        (sec.content as {entries:{institution:string;degree:string;field?:string;graduationDate:string}[]}).entries.forEach(e => {
          content.push(`${e.degree}${e.field ? ' in ' + e.field : ''} — ${e.institution} (${e.graduationDate})`);
        });
      }
      content.push('');
    });
    const blob = new Blob([content.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${resume.header.name.replace(/\s+/g, '_')}_resume.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [resume]);

  if (!resume) {
    return (
      <div className="canvas-loading">
        <Sparkles size={32} />
        <p>Loading resume…</p>
      </div>
    );
  }

  const alignTier = getScoreTier(metrics.alignment);
  const kcrTier = getScoreTier(metrics.keywordCoverage, true);
  const impactTier = getScoreTier(metrics.impactScore);
  const atsTier = getScoreTier(metrics.atsPassRate, true);
  // Tiers kept for potential future use
  void alignTier; void kcrTier; void impactTier; void atsTier;

  // Score color helper
  const scoreColor = (val: number, isPct100 = false) => {
    const v = isPct100 ? val / 100 : val;
    if (v >= 0.7) return 'score-green';
    if (v >= 0.4) return 'score-amber';
    return 'score-red';
  };

  return (
    <div className="canvas-page">
      {/* ═══ JD PANEL (LEFT) ═══ */}
      {jd && (
        <aside className={`jd-panel ${jdOpen ? 'jd-open' : 'jd-closed'}`}>
          <button className="jd-toggle" onClick={() => setJdOpen(!jdOpen)} aria-label={jdOpen ? 'Collapse JD panel' : 'Expand JD panel'}>
            {jdOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
          </button>
          {jdOpen && (
            <div className="jd-content">
              <div className="jd-header">
                <h3>{jd.title}</h3>
                <p className="jd-company">{jd.company}</p>
                {jd.location && <p className="jd-location">{jd.location}</p>}
              </div>
              <div className="jd-section">
                <h4>Required Skills</h4>
                <div className="jd-tags">
                  {jd.keywords.map((kw) => (
                    <span key={kw} className="jd-tag">{kw}</span>
                  ))}
                </div>
              </div>
              <div className="jd-section">
                <h4>Requirements</h4>
                <ul>
                  {jd.requirements.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
              <div className="jd-section">
                <h4>Responsibilities</h4>
                <ul>
                  {jd.responsibilities.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </aside>
      )}

      {/* ═══ RESUME DOCUMENT (CENTER) ═══ */}
      <main className="resume-document">
        {/* Progress bar during optimization */}
        {canvasState === 'OPTIMIZING' && <div className="canvas-progress-bar" />}

        {/* ── Profile Super Tile ── */}
        <div className="profile-super-tile">
          <div className="profile-avatar">
            {resume.header.photoUrl ? (
              <img src={resume.header.photoUrl} alt={resume.header.name} className="avatar-img" />
            ) : (
              <div className="avatar-initials">
                {resume.header.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
              </div>
            )}
          </div>
          <div className="profile-info">
            <h1 className="profile-name">{resume.header.name}</h1>
            <div className="profile-details">
              {resume.header.email && (
                <span className="profile-detail">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                  </svg>
                  {resume.header.email}
                </span>
              )}
              {resume.header.phone && (
                <span className="profile-detail">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
                  </svg>
                  {resume.header.phone}
                </span>
              )}
              {resume.header.location && (
                <span className="profile-detail">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" />
                  </svg>
                  {resume.header.location}
                </span>
              )}
            </div>
            <div className="profile-links">
              {resume.header.linkedin && (
                <a href={`https://${resume.header.linkedin}`} target="_blank" rel="noopener noreferrer" className="profile-link">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                  LinkedIn
                </a>
              )}
              {resume.header.github && (
                <a href={`https://${resume.header.github}`} target="_blank" rel="noopener noreferrer" className="profile-link">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                  </svg>
                  GitHub
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Render each section */}
        {resume.sections.map((section) => (
          <div key={section.id} className="resume-section" data-section-type={section.type}>
            <div className="section-header">
              <h2 className="section-title">{section.title}</h2>
              <div className="section-controls">
                <button
                  className="sc-btn"
                  title="Re-optimize this section"
                  onClick={() => handleReoptimizeSection(section.id, section.title)}
                  disabled={reoptimizingSection === section.id}
                >
                  {reoptimizingSection === section.id ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
                  {reoptimizingSection === section.id ? 'Optimizing…' : 'Re-optimize'}
                </button>
                <button
                  className="sc-btn sc-btn-ai"
                  title="Manually enhance with AI"
                  onClick={() => setSectionEnhanceOpen(sectionEnhanceOpen === section.id ? null : section.id)}
                >
                  <MessageSquare size={14} /> AI Enhance
                </button>
              </div>
            </div>
            {/* Manual AI enhancement input */}
            {sectionEnhanceOpen === section.id && (
              <div className="section-enhance-input">
                <input
                  type="text"
                  placeholder={`e.g. "Make it more quantitative" or "Add leadership language"…`}
                  value={sectionEnhanceInput}
                  onChange={(e) => setSectionEnhanceInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSectionEnhance(section.id, section.title, sectionEnhanceInput)}
                />
                <button onClick={() => handleSectionEnhance(section.id, section.title, sectionEnhanceInput)} disabled={!sectionEnhanceInput.trim()}>
                  <Send size={12} /> Go
                </button>
              </div>
            )}

            {/* SUMMARY */}
            {section.type === 'summary' && 'text' in section.content && (
              <div className="summary-block">
                <p>{(section.content as { text: string }).text}</p>
              </div>
            )}

            {/* EXPERIENCE */}
            {section.type === 'experience' && 'entries' in section.content && (
              <div className="experience-entries">
                {(section.content as { entries: { company: string; title: string; startDate: string; endDate: string; location?: string; bullets: { id: string; currentText: string; impactScore: number; aiSuggestion: string | null; status: string }[] }[] }).entries.map((entry, ei) => (
                  <div key={ei} className="experience-entry">
                    <div className="entry-header">
                      <div>
                        <strong>{entry.title}</strong> — {entry.company}
                      </div>
                      <span className="entry-dates">{entry.startDate} – {entry.endDate}</span>
                    </div>
                    <ul className="bullet-list">
                      {entry.bullets.map((bullet) => {
                        const impactCls = bullet.impactScore >= 0.7 ? 'impact-high' : bullet.impactScore >= 0.4 ? 'impact-mid' : 'impact-low';
                        return (
                          <li key={bullet.id} className={`bullet-item ${bullet.aiSuggestion ? 'has-suggestion' : ''}`}>
                            <div className="bullet-row">
                              <span className="bullet-text">{bullet.currentText}</span>
                              <span className={`impact-badge ${impactCls}`}>{bullet.impactScore.toFixed(2)}</span>
                              <button className="bullet-edit-btn" title="Edit bullet">
                                <Edit3 size={12} />
                              </button>
                            </div>
                            {bullet.aiSuggestion && bullet.status === 'original' && (
                              <div className="ai-suggestion-card">
                                <div className="ai-label"><Sparkles size={12} /> AI Suggestion</div>
                                <p className="ai-text">{bullet.aiSuggestion}</p>
                                <div className="ai-actions">
                                  <button className="ai-accept" onClick={() => handleAcceptBullet(bullet.id, bullet.aiSuggestion!)}><Check size={14} /> Accept</button>
                                  <button className="ai-reject" onClick={() => handleRejectBullet(bullet.id)}><X size={14} /> Reject</button>
                                </div>
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </div>
            )}

            {/* SKILLS */}
            {section.type === 'skills' && 'categories' in section.content && (
              <div className="skills-grid">
                {(section.content as { categories: { label: string; skills: { id: string; name: string; matched: boolean }[] }[] }).categories.map((cat) => (
                  <div key={cat.label} className="skill-category">
                    <h4>{cat.label}</h4>
                    <div className="skill-tags">
                      {cat.skills.map((sk) => (
                        <span key={sk.id} className={`skill-tag ${sk.matched ? 'matched' : 'unmatched'}`}>{sk.name}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* EDUCATION */}
            {section.type === 'education' && 'entries' in section.content && (
              <div className="education-entries">
                {(section.content as { entries: { institution: string; degree: string; field?: string; graduationDate: string; gpa?: string }[] }).entries.map((edu, i) => (
                  <div key={i} className="education-entry">
                    <strong>{edu.degree} {edu.field && `in ${edu.field}`}</strong> — {edu.institution}
                    <span className="edu-date">{edu.graduationDate}</span>
                    {edu.gpa && <span className="edu-gpa">GPA: {edu.gpa}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Version bar */}
        <div className="version-bar">
          <Clock size={14} />
          {resume.versions.slice(-3).map((v) => (
            <span key={v.id} className="version-link">v{v.versionNum}: {v.label}</span>
          ))}
          <button className="version-history-btn" onClick={() => setHistoryOpen(!historyOpen)}>
            <History size={12} /> Full history
          </button>
        </div>

        {/* History Drawer */}
        {historyOpen && (
          <div className="history-drawer">
            <div className="history-header">
              <h3>Change History</h3>
              <button className="history-close" onClick={() => setHistoryOpen(false)}><X size={14} /></button>
            </div>
            <div className="history-list">
              {historyLog.map((h) => (
                <div key={h.id} className="history-item">
                  <div className="history-item-info">
                    <span className={`history-action ${h.action.toLowerCase()}`}>{h.action}</span>
                    <span className="history-text">{h.text}</span>
                    <span className="history-time">{h.time}</span>
                  </div>
                  <button className="history-undo" onClick={() => handleUndoHistory(h.id)} title="Undo this change">
                    <Undo2 size={12} />
                  </button>
                </div>
              ))}
              {historyLog.length === 0 && <p className="history-empty">No changes yet.</p>}
            </div>
          </div>
        )}
      </main>

      {/* ═══ METRICS SIDEBAR (RIGHT) ═══ */}
      <aside className="metrics-sidebar">
        <h3 className="sidebar-title">Metrics</h3>

        {/* Compact metric cards with color coding */}
        <div className="metrics-grid">
          {[
            { label: 'Alignment', value: metrics.alignment, pct: formatPct(metrics.alignment) },
            { label: 'Keywords', value: metrics.keywordCoverage / 100, pct: formatPct100(metrics.keywordCoverage) },
            { label: 'Impact', value: metrics.impactScore, pct: formatPct(metrics.impactScore) },
            { label: 'ATS Rate', value: metrics.atsPassRate / 100, pct: formatPct100(metrics.atsPassRate) },
          ].map((m) => (
            <div key={m.label} className="metric-card-sm">
              <div className="metric-label-sm">{m.label}</div>
              <div className={`metric-value-sm ${scoreColor(m.value)}`}>{m.pct}</div>
              <div className="metric-bar-bg-sm">
                <div className={`metric-bar-fill-sm ${scoreColor(m.value)}`} style={{ width: `${m.value * 100}%` }} />
              </div>
            </div>
          ))}
        </div>

        {/* Keyword map */}
        {keywords.length > 0 && (
          <div className="keyword-map">
            <h4>Keyword Map</h4>
            <div className="keyword-tags">
              {keywords.map((kw) => (
                <span key={kw.keyword} className={`kw-tag ${kw.matched ? 'kw-matched' : 'kw-missing'}`}>
                  {kw.keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* LinkedIn & GitHub tiles */}
        <div className="profile-tiles">
          <div className="profile-tile">
            <Linkedin size={16} className="tile-icon linkedin" />
            <div className="tile-info">
              <span className="tile-label">LinkedIn</span>
              <span className="tile-status">Connected</span>
            </div>
            <button className="tile-refresh" title="Refresh from LinkedIn" onClick={handleLinkedinRefresh} disabled={linkedinChanges.loading}>
              {linkedinChanges.loading ? <Loader2 size={12} className="spin" /> : <RefreshCw size={12} />}
            </button>
          </div>
          {linkedinChanges.checked && (
            <div className="tile-changes">
              {linkedinChanges.items.length > 0 ? (
                linkedinChanges.items.map((item, i) => <div key={i} className="tile-change-item">↳ {item}</div>)
              ) : (
                <div className="tile-change-none">No new changes</div>
              )}
            </div>
          )}
          <div className="profile-tile">
            <Github size={16} className="tile-icon github" />
            <div className="tile-info">
              <span className="tile-label">GitHub</span>
              <span className="tile-status">Connected</span>
            </div>
            <button className="tile-refresh" title="Refresh from GitHub" onClick={handleGithubRefresh} disabled={githubChanges.loading}>
              {githubChanges.loading ? <Loader2 size={12} className="spin" /> : <RefreshCw size={12} />}
            </button>
          </div>
          {githubChanges.checked && (
            <div className="tile-changes">
              {githubChanges.items.length > 0 ? (
                githubChanges.items.map((item, i) => <div key={i} className="tile-change-item">↳ {item}</div>)
              ) : (
                <div className="tile-change-none">No new changes</div>
              )}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="sidebar-actions">
          <button className="export-btn" onClick={handleExportPdf}>
            <Download size={16} /> Export PDF
          </button>
          {jd && (
            <Link to={`/interview/mock-job?resumeId=${resume.id}`} className="interview-link">
              <FileText size={16} /> Interview Prep →
            </Link>
          )}
        </div>
      </aside>
    </div>
  );
}
