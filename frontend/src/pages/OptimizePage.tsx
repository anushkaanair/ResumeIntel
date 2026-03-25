/**
 * OptimizePage — Upload resume + paste JD → start optimization → redirect to canvas.
 * Route: /optimize
 */
import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  FileText,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Briefcase,
  ClipboardPaste,
  X,
  Linkedin,
  Github,
  Link as LinkIcon,
  User,
} from 'lucide-react';
import * as pdfjsLib from 'pdfjs-dist';
import './OptimizePage.css';

// Configure PDF.js worker — v3.x uses .js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

/** Extract all text from a PDF File using pdf.js */
async function extractPdfText(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(arrayBuffer) });
  const pdf = await loadingTask.promise;
  const pages: string[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const strings = content.items.map((item: any) => item.str as string);
    pages.push(strings.join(' '));
  }
  return pages.join('\n');
}

type UploadState = 'idle' | 'dragging' | 'uploading' | 'uploaded' | 'error';

export function OptimizePage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [candidateName, setCandidateName] = useState('');
  const [jdText, setJdText] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState('');

  // ── Drag & Drop handlers ──
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setUploadState('dragging');
  }, []);

  const handleDragLeave = useCallback(() => {
    setUploadState((s) => (s === 'dragging' ? 'idle' : s));
  }, []);

  const processFile = useCallback((file: File) => {
    const validTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|docx?|txt)$/i)) {
      setError('Please upload a PDF, DOCX, or TXT file.');
      setUploadState('error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File must be under 10MB.');
      setUploadState('error');
      return;
    }

    setError('');
    setUploadState('uploading');
    setFileName(file.name);
    setFileSize(`${(file.size / 1024).toFixed(0)} KB`);

    if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
      // Plain text — read directly
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        if (text) setResumeText(text);
        setUploadState('uploaded');
      };
      reader.onerror = () => setUploadState('uploaded');
      reader.readAsText(file);
    } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
      // PDF — extract full text using pdf.js
      extractPdfText(file)
        .then((text) => {
          console.log('[ResumeIntel] Extracted PDF text:', text.substring(0, 200) + '...');
          setResumeText(text);
          setUploadState('uploaded');
        })
        .catch((err) => {
          console.error('[ResumeIntel] PDF extraction error:', err);
          setError('Could not parse PDF. Try uploading a .txt file instead.');
          setUploadState('error');
        });
    } else {
      // DOCX or other — store filename, text extraction not yet supported client-side
      setResumeText(`[Uploaded: ${file.name}]`);
      setTimeout(() => setUploadState('uploaded'), 1200);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const removeFile = useCallback(() => {
    setUploadState('idle');
    setFileName('');
    setFileSize('');
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  // ── Start optimization ──
  const canStart = uploadState === 'uploaded' && jdText.trim().length > 30;

  const handleOptimize = useCallback(async () => {
    if (!canStart) return;
    setIsOptimizing(true);

    // Store all user input in sessionStorage for the Canvas page
    sessionStorage.setItem('ri_resume_text', resumeText);
    sessionStorage.setItem('ri_resume_filename', fileName);
    sessionStorage.setItem('ri_user_name', candidateName.trim());
    sessionStorage.setItem('ri_jd_text', jdText);
    sessionStorage.setItem('ri_linkedin_url', linkedinUrl);
    sessionStorage.setItem('ri_github_url', githubUrl);

    // Simulate API processing delay
    await new Promise((r) => setTimeout(r, 2000));

    // Generate IDs and redirect to canvas
    const resumeId = `resume-${Date.now().toString(36)}`;
    const jdId = `jd-${Date.now().toString(36)}`;
    navigate(`/canvas/${resumeId}?jdId=${jdId}`);
  }, [canStart, navigate, resumeText, fileName, candidateName, jdText, linkedinUrl, githubUrl]);

  return (
    <div className="optimize-page">
      {/* Background glow */}
      <div className="optimize-bg-glow" />

      <div className="optimize-container">
        {/* Header */}
        <div className="optimize-header">
          <div className="optimize-pill">
            <span className="optimize-dot" />
            AI-POWERED OPTIMIZATION
          </div>
          <h1 className="optimize-title">
            Optimize Your <span className="gradient-text">Resume</span>
          </h1>
          <p className="optimize-subtitle">
            Upload your resume and paste the job description. Our AI agents will analyze, score, and enhance every bullet.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="optimize-grid">
          {/* ═══ LEFT: Resume Upload ═══ */}
          <div className="optimize-card">
            <div className="card-header">
              <FileText size={20} className="card-icon" />
              <div>
                <h2 className="card-title">Resume</h2>
                <p className="card-desc">Upload your current resume file</p>
              </div>
            </div>

            {uploadState === 'uploaded' ? (
              <div className="file-uploaded">
                <div className="file-info">
                  <CheckCircle2 size={24} className="file-check" />
                  <div>
                    <p className="file-name">{fileName}</p>
                    <p className="file-meta">{fileSize} • Ready for optimization</p>
                  </div>
                </div>
                <button className="file-remove" onClick={removeFile} title="Remove file">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div
                className={`drop-zone ${uploadState === 'dragging' ? 'drop-active' : ''} ${uploadState === 'error' ? 'drop-error' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.doc,.docx,.txt"
                  className="file-input-hidden"
                  onChange={handleFileSelect}
                />
                {uploadState === 'uploading' ? (
                  <div className="drop-uploading">
                    <Loader2 size={32} className="spin" />
                    <p>Processing {fileName}…</p>
                  </div>
                ) : (
                  <>
                    <div className="drop-icon">
                      <Upload size={28} />
                    </div>
                    <p className="drop-text">
                      <strong>Drop your resume here</strong> or click to browse
                    </p>
                    <p className="drop-formats">Supports PDF, DOCX, TXT • Max 10MB</p>
                  </>
                )}
              </div>
            )}

            {error && (
              <div className="upload-error">
                <AlertCircle size={14} /> {error}
              </div>
            )}
          </div>

          {/* ═══ RIGHT: Job Description ═══ */}
          <div className="optimize-card">
            <div className="card-header">
              <Briefcase size={20} className="card-icon" />
              <div>
                <h2 className="card-title">Job Description</h2>
                <p className="card-desc">Paste the target JD for tailoring</p>
              </div>
            </div>

            <div className="jd-input-wrapper">
              <textarea
                className="jd-textarea"
                placeholder={"Paste the full job description here...\n\nInclude the role title, requirements, responsibilities, and qualifications for the best results."}
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                aria-label="Job description text"
              />
              <div className="jd-meta">
                <span className={jdText.length > 30 ? 'jd-char-ok' : 'jd-char-warn'}>
                  {jdText.length} characters
                </span>
                {jdText.length < 30 && (
                  <span className="jd-hint">
                    <ClipboardPaste size={12} /> Minimum 30 characters
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ═══ NAME INPUT ═══ */}
        <div className="optimize-card profiles-card">
          <div className="card-header">
            <User size={20} className="card-icon" />
            <div>
              <h2 className="card-title">Your Name</h2>
              <p className="card-desc">This will appear at the top of your optimized resume</p>
            </div>
          </div>
          <div className="profile-inputs">
            <div className="profile-input-group" style={{ flex: 1 }}>
              <input
                type="text"
                className="profile-input"
                placeholder="e.g. Anushka Nair"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                aria-label="Your full name"
                style={{ fontSize: '1.05rem' }}
              />
            </div>
          </div>
        </div>

        {/* ═══ PROFILES: LinkedIn & GitHub ═══ */}
        <div className="optimize-card profiles-card">
          <div className="card-header">
            <LinkIcon size={20} className="card-icon" />
            <div>
              <h2 className="card-title">Your Profiles</h2>
              <p className="card-desc">Add your LinkedIn and GitHub for richer analysis</p>
            </div>
          </div>

          <div className="profile-inputs">
            <div className="profile-input-group">
              <label className="profile-input-label">
                <Linkedin size={16} />
                LinkedIn URL
              </label>
              <input
                type="url"
                className="profile-input"
                placeholder="https://linkedin.com/in/yourname"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                aria-label="LinkedIn profile URL"
              />
            </div>
            <div className="profile-input-group">
              <label className="profile-input-label">
                <Github size={16} />
                GitHub URL
              </label>
              <input
                type="url"
                className="profile-input"
                placeholder="https://github.com/yourname"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                aria-label="GitHub profile URL"
              />
            </div>
          </div>

          {(linkedinUrl || githubUrl) && (
            <div className="profiles-status">
              <CheckCircle2 size={14} className="file-check" />
              {[linkedinUrl && 'LinkedIn', githubUrl && 'GitHub'].filter(Boolean).join(' & ')} linked
            </div>
          )}
        </div>

        {/* ═══ Start Optimization CTA ═══ */}
        <div className="optimize-cta-section">
          <button
            className={`optimize-launch-btn ${canStart ? '' : 'disabled'}`}
            onClick={handleOptimize}
            disabled={!canStart || isOptimizing}
          >
            {isOptimizing ? (
              <>
                <Loader2 size={18} className="spin" />
                Initializing AI Pipeline…
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Start Optimization
                <ArrowRight size={16} />
              </>
            )}
          </button>
          {!canStart && !isOptimizing && (
            <p className="cta-hint">
              {uploadState !== 'uploaded'
                ? 'Upload your resume to continue'
                : 'Paste a job description (min 30 characters)'}
            </p>
          )}
        </div>

        {/* ═══ How It Works Steps ═══ */}
        <div className="optimize-steps">
          {[
            { num: '01', title: 'Upload', desc: 'Your resume is parsed and structured by our ingestion agent.' },
            { num: '02', title: 'Analyze', desc: '5 specialized AI agents score alignment, impact, and ATS compatibility.' },
            { num: '03', title: 'Optimize', desc: 'Each bullet gets AI-enhanced suggestions you can accept, reject, or tweak.' },
          ].map((step) => (
            <div key={step.num} className="optimize-step">
              <span className="step-num">{step.num}</span>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-desc">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
