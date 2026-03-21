# Resume Intel — Frontend Developer Documentation

> **For:** Frontend teammate (UI/UX developer)
> **From:** Neel (AI + Backend lead)
> **Last updated:** 2026-03-21
> **Status:** Backend API is live, AI pipeline functional. Frontend scaffolding exists — needs full UI build-out.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Getting Started — Setup & Dev Environment](#2-getting-started)
3. [Tech Stack & Dependencies](#3-tech-stack--dependencies)
4. [Folder Structure](#4-folder-structure)
5. [Routing & Page Map](#5-routing--page-map)
6. [Complete API Reference (All Endpoints)](#6-complete-api-reference)
7. [Existing Components (Already Built)](#7-existing-components)
8. [Existing Hooks (Already Built)](#8-existing-hooks)
9. [Pages — Current State & What Needs Building](#9-pages--what-needs-building)
10. [UI/UX Design Spec — Every Screen](#10-uiux-design-spec)
11. [State Management & Data Flow](#11-state-management--data-flow)
12. [Code Conventions & Patterns](#12-code-conventions--patterns)
13. [PDF Import Feature (Already Integrated)](#13-pdf-import-feature)
14. [Components To Build](#14-components-to-build)
15. [TypeScript Types & Interfaces](#15-typescript-types--interfaces)
16. [Error Handling Patterns](#16-error-handling-patterns)
17. [Animation & Motion Guidelines](#17-animation--motion-guidelines)
18. [Responsive Design Breakpoints](#18-responsive-design-breakpoints)
19. [Accessibility Requirements](#19-accessibility-requirements)
20. [Git Workflow & Team Coordination](#20-git-workflow)
21. [Testing](#21-testing)

---

## 1. Project Overview

**Resume Intel** is an AI-powered resume optimization platform. Users upload a resume (PDF/DOCX/TXT or paste text), provide a target job description, and the system runs a 6-agent AI pipeline that:

1. Parses and segments the resume
2. Generates optimized, metrics-driven bullet points
3. Enforces quality standards (quality gate >= 0.7)
4. Detects weaknesses and gaps
5. Tailors content to the specific job description (alignment gate >= 0.6)
6. Generates interview preparation materials

The frontend is a **single-page React dashboard** that handles file upload, pipeline execution, real-time status polling, and rich results display.

---

## 2. Getting Started

### Prerequisites
- Node.js 18+ and npm 9+
- The backend must be running on `http://localhost:8000` (Neel handles this)

### Setup
```bash
# Clone the repo
git clone <repo-url>
cd resume-intel/frontend

# Install dependencies
npm install

# Start dev server (auto-proxies /api/* to backend on port 8000)
npm run dev
# App runs on http://localhost:5173
```

### Available Scripts
| Command | What it does |
|---------|-------------|
| `npm run dev` | Start Vite dev server on port 5173 with HMR |
| `npm run build` | TypeScript check + production build |
| `npm run preview` | Preview production build locally |
| `npm run lint` | ESLint check across all .ts/.tsx files |

### Environment Variables
Create `frontend/.env.local` (optional — defaults work for local dev):
```env
VITE_API_URL=http://localhost:8000/api/v1
```

### Vite Proxy (already configured)
`vite.config.ts` proxies all `/api/*` requests to `http://localhost:8000`, so you never hit CORS issues in dev:
```ts
server: {
  port: 5173,
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
},
```

---

## 3. Tech Stack & Dependencies

### Production Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^18.2.0 | UI framework |
| `react-dom` | ^18.2.0 | React DOM renderer |
| `react-router-dom` | ^6.21.0 | Client-side routing |
| `framer-motion` | ^10.18.0 | Animations & transitions |
| `axios` | ^1.6.0 | HTTP client for API calls |

### Dev Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `typescript` | ^5.3.3 | Type safety |
| `vite` | ^5.0.8 | Build tool & dev server |
| `@vitejs/plugin-react` | ^4.2.1 | React Fast Refresh for Vite |
| `tailwindcss` | ^3.4.0 | Utility-first CSS framework |
| `autoprefixer` | ^10.4.16 | CSS vendor prefixes |
| `postcss` | ^8.4.32 | CSS processing |
| `eslint` | ^8.55.0 | Linting |
| `@types/react` | ^18.2.43 | React type definitions |
| `@types/react-dom` | ^18.2.17 | ReactDOM type definitions |

### Recommended Additions (install when needed)
```bash
# Icons
npm install lucide-react        # or react-icons

# Toast notifications
npm install react-hot-toast     # or sonner

# Form validation (if auth pages are added)
npm install react-hook-form zod @hookform/resolvers

# Date formatting
npm install date-fns
```

---

## 4. Folder Structure

```
frontend/
├── public/                     # Static assets (favicon, etc.)
├── src/
│   ├── components/             # Reusable UI components
│   │   ├── AlignmentGauge.tsx  # [EXISTS] Score visualization circle
│   │   ├── Button.tsx          # [EXISTS] Primary/secondary/ghost button
│   │   ├── Card.tsx            # [EXISTS] Container card with title
│   │   ├── LoadingSpinner.tsx  # [EXISTS] Spinning loader + message
│   │   ├── PdfUploadZone.tsx   # [EXISTS] Drag-drop file upload
│   │   ├── ScoreBadge.tsx      # [EXISTS] Colored score pill
│   │   ├── SuggestionList.tsx  # [EXISTS] Warning-style suggestion list
│   │   │
│   │   │   ── TO BUILD ──
│   │   ├── Navbar.tsx          # [TODO] Top navigation bar
│   │   ├── Footer.tsx          # [TODO] Page footer
│   │   ├── ProgressTracker.tsx # [TODO] Pipeline step progress
│   │   ├── KeywordChips.tsx    # [TODO] Matched/missing keyword pills
│   │   ├── ResumePreview.tsx   # [TODO] Side-by-side original vs optimized
│   │   ├── InterviewCard.tsx   # [TODO] Single interview Q&A card
│   │   ├── ExportButtons.tsx   # [TODO] PDF/DOCX download buttons
│   │   ├── ScoreRadar.tsx      # [TODO] Radar chart for section scores
│   │   ├── WeaknessCard.tsx    # [TODO] Individual weakness display
│   │   └── EmptyState.tsx      # [TODO] Empty/placeholder state
│   │
│   ├── pages/                  # Route-level page components
│   │   ├── HomePage.tsx        # [EXISTS - SKELETAL] Landing page
│   │   ├── OptimizePage.tsx    # [EXISTS - FUNCTIONAL] Upload + JD input
│   │   ├── ResultsPage.tsx     # [EXISTS - FUNCTIONAL] Results display
│   │   │
│   │   │   ── TO BUILD ──
│   │   ├── DashboardPage.tsx   # [TODO] User's optimization history
│   │   └── InterviewPrepPage.tsx # [TODO] Dedicated interview prep view
│   │
│   ├── hooks/                  # Custom React hooks
│   │   ├── useJobStatus.ts     # [EXISTS] Polls job status, fetches result
│   │   ├── useOptimize.ts      # [EXISTS] Triggers optimization pipeline
│   │   │
│   │   │   ── TO BUILD ──
│   │   ├── useAlignment.ts     # [TODO] Calls alignment score endpoint
│   │   └── useExport.ts        # [TODO] Handles PDF/DOCX export download
│   │
│   ├── lib/                    # Utilities, API client, constants
│   │   ├── api.ts              # [EXISTS] Axios instance + all API functions
│   │   │
│   │   │   ── TO BUILD ──
│   │   ├── constants.ts        # [TODO] App-wide constants
│   │   ├── utils.ts            # [TODO] Helper functions
│   │   └── types.ts            # [TODO] Shared TypeScript interfaces
│   │
│   ├── App.tsx                 # [EXISTS] Root component + router
│   └── main.tsx                # [EXISTS] Entry point
│
├── .env.local                  # Local env overrides (gitignored)
├── index.html                  # HTML shell
├── package.json                # Dependencies & scripts
├── tailwind.config.js          # Tailwind configuration
├── tsconfig.json               # TypeScript configuration
└── vite.config.ts              # Vite build config + proxy
```

---

## 5. Routing & Page Map

### Current Routes (in `App.tsx`)
| Route | Component | Status | Purpose |
|-------|-----------|--------|---------|
| `/` | `HomePage` | Skeletal | Landing page with CTA |
| `/optimize` | `OptimizePage` | Functional | Resume upload + JD input |
| `/results/:jobId` | `ResultsPage` | Functional | Pipeline results display |

### Routes To Add
| Route | Component | Purpose |
|-------|-----------|---------|
| `/dashboard` | `DashboardPage` | History of past optimizations |
| `/interview/:jobId` | `InterviewPrepPage` | Expanded interview prep view |

### Navigation Flow
```
HomePage  ──[Get Started]──>  OptimizePage
                                   │
                         [Paste text OR Import PDF]
                         [Paste Job Description]
                         [Click "Optimize Resume"]
                                   │
                                   v
                            ResultsPage (:jobId)
                              ├── Score overview (gauges)
                              ├── Pipeline scores (badges)
                              ├── Optimized resume (preview)
                              ├── Weakness suggestions
                              ├── Keyword coverage
                              ├── Interview prep section
                              └── Export buttons (PDF / DOCX)
                                   │
                          [View Full Interview Prep]
                                   │
                                   v
                         InterviewPrepPage (:jobId)
```

---

## 6. Complete API Reference

**Base URL:** `http://localhost:8000/api/v1` (proxied via Vite in dev)

**Response Format (ALL endpoints):**
```typescript
// Success
{ status: "ok", data: { ... }, meta?: { ... } }

// Error
{ status: "error", error: { code: string, message: string } }
```

### 6.1 Upload Resume
```
POST /api/v1/resume/upload
Content-Type: multipart/form-data
```

**Request:** FormData with `file` field (PDF, DOCX, DOC, or TXT, max 5MB)

**Response (201):**
```json
{
  "status": "ok",
  "data": {
    "text": "John Doe\nSenior Software Engineer\n...",
    "filename": "john_doe_resume.pdf",
    "chars": 3842
  }
}
```

**Frontend function:** `uploadResume(file: File)` in `lib/api.ts`

**Error codes:**
| Code | When |
|------|------|
| `INVALID_FILE_TYPE` | Not PDF/DOCX/DOC/TXT |
| `FILE_TOO_LARGE` | Exceeds 5MB |
| `PARSE_FAILED` | Text extraction failed (image-based PDF, corrupted file) |

---

### 6.2 Run Optimization Pipeline
```
POST /api/v1/optimize
Content-Type: application/json
```

**Request:**
```json
{
  "resume_text": "John Doe\nSenior Software Engineer...",
  "job_description": "We are looking for a Senior Backend Engineer...",
  "options": {
    "skip_interview_prep": false,
    "quality_threshold": 0.7,
    "max_retries": 3
  }
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `resume_text` | string | Yes | min 50 chars |
| `job_description` | string | Yes | min 20 chars |
| `options` | object | No | Optional overrides |
| `options.skip_interview_prep` | boolean | No | Default: false |
| `options.quality_threshold` | float | No | 0.0-1.0, default: 0.7 |
| `options.max_retries` | int | No | 1-5, default: 3 |

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "job_id": "660e8400-e29b-41d4-a716-446655440001",
    "message": "Optimization pipeline completed"
  }
}
```

**Frontend function:** `startOptimization(resumeText, jobDescription)` in `lib/api.ts`

> **Note:** Currently runs synchronously (returns when done). Will become async (202 Accepted) when Celery is integrated — frontend already handles polling via `useJobStatus`.

---

### 6.3 Check Optimization Status
```
GET /api/v1/optimize/{job_id}/status
```

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "job_id": "660e8400-e29b-41d4-a716-446655440001",
    "job_status": "completed"
  }
}
```

**`job_status` values:**
| Value | Meaning | Frontend behavior |
|-------|---------|-------------------|
| `"queued"` | Waiting for worker | Show spinner + "Queued..." |
| `"running"` | Pipeline executing | Show spinner + "Running..." + progress |
| `"completed"` | Done, results ready | Stop polling, fetch result |
| `"failed"` | Pipeline error | Stop polling, show error |
| `"not_found"` | Invalid job ID | Show "not found" error |

**Frontend function:** `getOptimizationStatus(jobId)` in `lib/api.ts`
**Frontend hook:** `useJobStatus(jobId)` — auto-polls every 2 seconds

---

### 6.4 Get Optimization Results
```
GET /api/v1/optimize/{job_id}/result
```

**Response (200) — Full result structure:**
```json
{
  "status": "ok",
  "data": {
    "status": "completed",
    "results": {
      "ingestion": {
        "content": "Parsed resume text with section markers...",
        "quality_score": 0.85,
        "suggestions": [],
        "metadata": {
          "sections_found": ["summary", "experience", "education", "skills"],
          "segment_count": 18
        }
      },
      "generation": {
        "content": "## Experience\n- Architected 12 microservices handling 50K RPM...",
        "quality_score": 0.82,
        "suggestions": [
          "Consider adding metrics to the education section",
          "Project descriptions could include tech stack details"
        ],
        "metadata": {}
      },
      "quality": {
        "content": "Quality-verified optimized content...",
        "quality_score": 0.78,
        "suggestions": [
          "Bullet 3 in experience lacks quantifiable outcome",
          "Skills section could be reorganized by proficiency"
        ],
        "metadata": {}
      },
      "weak_detection": {
        "content": "Weakness analysis report...",
        "quality_score": 0.71,
        "suggestions": [
          "No mention of container orchestration (Kubernetes)",
          "Infrastructure-as-code experience not evident",
          "Employment gap detected: Jun 2023 - Sep 2023"
        ],
        "metadata": {}
      },
      "tailoring": {
        "content": "# John Doe\n## Senior Backend Engineer\n\n## Summary\nResults-driven engineer...\n\n## Experience\n- Architected and deployed 12 microservices...",
        "quality_score": 0.76,
        "suggestions": [],
        "metadata": {
          "alignment_score": 0.72,
          "matched_keywords": ["Python", "microservices", "AWS", "PostgreSQL"],
          "missing_keywords": ["Kubernetes", "CI/CD", "Terraform"]
        }
      },
      "interview": {
        "content": "## Interview Preparation\n\n### Behavioral Questions\n1. Tell me about a time you optimized system performance...\n\n### Technical Questions\n1. How would you design a distributed caching layer?...\n\n### Talking Points\n- Event-driven microservices architecture...",
        "quality_score": 0.80,
        "suggestions": [],
        "metadata": {}
      }
    }
  }
}
```

**Per-agent result shape (consistent across all 6 agents):**
```typescript
interface AgentResult {
  content: string;          // Main output text (markdown-formatted)
  quality_score: number;    // 0.0 to 1.0
  suggestions: string[];    // Improvement suggestions (can be empty)
  metadata: Record<string, unknown>; // Agent-specific extra data
}
```

**Frontend function:** `getOptimizationResult(jobId)` in `lib/api.ts`

---

### 6.5 Get Alignment Score (Standalone)
```
POST /api/v1/alignment/score
Content-Type: application/json
```

**Request:**
```json
{
  "resume_text": "John Doe\nSenior Software Engineer...",
  "job_description": "We are looking for a Senior Backend Engineer..."
}
```

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "overall_score": 0.682,
    "gaps": [
      "No mention of container orchestration (Kubernetes)",
      "Infrastructure-as-code experience not evident",
      "CI/CD pipeline experience not highlighted",
      "Team leadership experience unclear",
      "Cloud architecture certifications missing"
    ],
    "section_scores": {
      "content": 0.682
    }
  }
}
```

**Frontend function:** `getAlignmentScore(resumeText, jobDescription)` in `lib/api.ts`

---

### 6.6 Export as PDF
```
POST /api/v1/export/pdf
Content-Type: application/json
```

**Request:**
```json
{
  "content": "# John Doe\n## Experience\n- Architected 12 microservices...",
  "filename": "john_doe_optimized"
}
```

**Response:** Binary PDF file download
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="john_doe_optimized.pdf"`

**Frontend usage:**
```typescript
const response = await api.post("/export/pdf", { content, filename }, {
  responseType: "blob",
});
const url = URL.createObjectURL(response.data);
const a = document.createElement("a");
a.href = url;
a.download = `${filename}.pdf`;
a.click();
URL.revokeObjectURL(url);
```

---

### 6.7 Export as DOCX
```
POST /api/v1/export/docx
Content-Type: application/json
```

**Request:** Same as PDF export
```json
{
  "content": "# John Doe\n## Experience\n- Architected 12 microservices...",
  "filename": "john_doe_optimized"
}
```

**Response:** Binary DOCX file download
- `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `Content-Disposition: attachment; filename="john_doe_optimized.docx"`

---

### API Rate Limits
| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /optimize` | 10 req | per minute |
| `GET /optimize/*/status` | 60 req | per minute |
| `GET /optimize/*/result` | 60 req | per minute |
| `POST /resume/upload` | 20 req | per minute |
| `POST /alignment/score` | 30 req | per minute |
| `POST /export/*` | 20 req | per minute |

Rate limit headers returned on every response:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1711012300
```

---

## 7. Existing Components (Already Built)

### 7.1 `Button` — `components/Button.tsx`
```typescript
interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "ghost";  // default: "primary"
  loading?: boolean;     // shows spinner
  type?: "button" | "submit" | "reset";
  className?: string;
}
```
- **Primary:** Blue bg, white text (`bg-blue-600`)
- **Secondary:** Gray bg, dark text
- **Ghost:** Transparent, gray text
- Has `whileTap` scale animation (0.97)
- Auto-disabled when `loading=true`

### 7.2 `Card` — `components/Card.tsx`
```typescript
interface CardProps {
  title?: string;        // Optional heading
  children: React.ReactNode;
  className?: string;
}
```
- White bg, rounded-xl, border, shadow-sm
- Fade-in + slide-up animation on mount

### 7.3 `AlignmentGauge` — `components/AlignmentGauge.tsx`
```typescript
interface AlignmentGaugeProps {
  score: number;         // 0.0 to 1.0
  label?: string;        // default: "Alignment"
}
```
- Displays percentage (score * 100)
- Color coding: green (>=75%), yellow (>=50%), red (<50%)
- Spring animation on mount

### 7.4 `ScoreBadge` — `components/ScoreBadge.tsx`
```typescript
interface ScoreBadgeProps {
  score: number;         // 0.0 to 1.0
  label: string;
}
```
- Inline pill/badge component
- Same color coding as AlignmentGauge

### 7.5 `LoadingSpinner` — `components/LoadingSpinner.tsx`
```typescript
interface LoadingSpinnerProps {
  size?: number;         // pixels, default: 40
  message?: string;      // text below spinner
}
```
- Blue spinning circle (border animation)
- Optional message fades in

### 7.6 `SuggestionList` — `components/SuggestionList.tsx`
```typescript
interface SuggestionListProps {
  suggestions: string[];
  title?: string;        // default: "Suggestions"
}
```
- Amber/warning-styled list items
- Staggered fade-in animation (50ms per item)
- Returns null if empty array

### 7.7 `PdfUploadZone` — `components/PdfUploadZone.tsx`
```typescript
interface PdfUploadZoneProps {
  onTextExtracted: (text: string, filename: string) => void;
}
```
- Drag-and-drop zone OR click-to-browse
- Accepts: `.pdf`, `.doc`, `.docx`, `.txt`
- States: `idle` | `dragging` | `uploading` | `success` | `error`
- Calls `uploadResume(file)` from `lib/api.ts`
- On success: calls `onTextExtracted(text, filename)`
- Animated transitions between states (AnimatePresence)
- Shows: file icon (idle), spinner (uploading), checkmark (success), X (error)
- "Replace file" button after success
- "Try again" button after error

---

## 8. Existing Hooks (Already Built)

### 8.1 `useOptimize` — `hooks/useOptimize.ts`
```typescript
interface UseOptimizeReturn {
  jobId: string | null;
  loading: boolean;
  error: string | null;
  optimize: (resumeText: string, jobDescription: string) => Promise<void>;
  reset: () => void;
}
```
- Calls `startOptimization()` API
- Returns `jobId` on success for use with `useJobStatus`

### 8.2 `useJobStatus` — `hooks/useJobStatus.ts`
```typescript
type JobStatus = "idle" | "queued" | "running" | "completed" | "failed";

interface JobResult {
  ingestion?: { content: string; quality_score: number; metadata: Record<string, unknown> };
  generation?: { content: string; quality_score: number; suggestions: string[] };
  quality?: { content: string; quality_score: number; suggestions: string[] };
  weak_detection?: { content: string; quality_score: number; suggestions: string[] };
  tailoring?: { content: string; quality_score: number; metadata: Record<string, unknown> };
  interview?: { content: string; quality_score: number };
}

interface UseJobStatusReturn {
  status: JobStatus;
  result: JobResult | null;
  error: string | null;
}
```
- Auto-polls `/optimize/{jobId}/status` every 2 seconds
- When `completed`: fetches full result from `/optimize/{jobId}/result`
- When `failed`: stops polling, sets error
- Cleans up interval on unmount

---

## 9. Pages — Current State & What Needs Building

### 9.1 `HomePage` — NEEDS REDESIGN
**Current:** Minimal centered text + "Get Started" link.
**Needs:**
- Hero section with compelling headline + subtitle
- Visual feature cards (3-4 features: AI optimization, ATS alignment, interview prep, export)
- How it works section (3-step flow)
- CTA button linking to `/optimize`
- Navbar at top
- Footer

### 9.2 `OptimizePage` — FUNCTIONAL, NEEDS POLISH
**Current:** Working two-column layout with paste/PDF toggle and JD input.
**Already has:**
- Mode toggle (Paste Text / Import PDF) with animated switching
- `PdfUploadZone` integration for file upload
- Textarea for paste mode with character counter
- JD textarea with character counter
- Validation (resume >= 50 chars, JD >= 20 chars)
- Error banner
- Submit button with loading state
- Navigates to `/results/{jobId}` on success

**Needs:**
- Navbar
- Better visual hierarchy
- Options panel (skip interview, quality threshold slider)
- Alignment score preview before full optimization (optional enhancement)

### 9.3 `ResultsPage` — FUNCTIONAL, NEEDS ENRICHMENT
**Current:** Shows scores, pipeline badges, optimized resume, suggestions, interview prep.
**Already has:**
- Status polling with loading states
- Score overview (3 gauges: JD Alignment, Quality Score, Agents Completed)
- Pipeline score badges per agent
- Optimized resume in a Card (pre-formatted)
- Suggestions list
- Interview prep in a Card
- "New Optimization" button
- Error + failed states

**Needs:**
- Keyword coverage section (matched vs missing chips)
- Export buttons (PDF / DOCX download)
- Side-by-side original vs optimized view
- Weakness cards with severity badges
- Better interview prep formatting (Q&A cards, not raw text)
- Section-level score breakdown
- Navbar

---

## 10. UI/UX Design Spec — Every Screen

### 10.1 Design System

**Color Palette:**
| Token | Tailwind | Hex | Usage |
|-------|----------|-----|-------|
| Primary | `blue-600` | `#2563EB` | Buttons, links, active states |
| Primary hover | `blue-700` | `#1D4ED8` | Button hover |
| Success | `green-500` | `#22C55E` | Scores >= 75%, success states |
| Warning | `yellow-500` | `#EAB308` | Scores 50-74%, suggestions |
| Danger | `red-500` | `#EF4444` | Scores < 50%, errors |
| Background | `gray-50` | `#F9FAFB` | Page background |
| Surface | `white` | `#FFFFFF` | Cards, panels |
| Text primary | `gray-900` | `#111827` | Headlines |
| Text secondary | `gray-600` | `#4B5563` | Body text |
| Text muted | `gray-400` | `#9CA3AF` | Helpers, counters |
| Border | `gray-200` | `#E5E7EB` | Card borders, dividers |

**Typography (Tailwind defaults — system font stack):**
| Element | Class | Size |
|---------|-------|------|
| Page title | `text-3xl font-bold` | 30px |
| Section heading | `text-xl font-semibold` | 20px |
| Card title | `text-lg font-semibold` | 18px |
| Body text | `text-sm` | 14px |
| Helper text | `text-xs text-gray-400` | 12px |
| Button text | `text-sm font-medium` | 14px |

**Spacing:**
- Page padding: `px-4 py-12` on `max-w-4xl mx-auto` (optimize) or `max-w-5xl` (results)
- Card padding: `p-6`
- Grid gap: `gap-4` to `gap-6`
- Section spacing: `space-y-6` or `mt-8`

**Border Radius:**
- Cards: `rounded-xl`
- Buttons: `rounded-lg`
- Badges: `rounded-full`
- Inputs: `rounded-lg`

---

### 10.2 HomePage Layout

```
┌──────────────────────────────────────────────────────────┐
│  [Navbar]  Logo    Resume Intel         [Get Started]    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│              AI-Powered Resume Optimization              │
│     Optimize your resume for ATS systems using a         │
│     6-agent AI pipeline with RAG-grounded generation     │
│                                                          │
│              [ Get Started → ]                           │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐              │
│   │  Upload  │   │ AI Opt. │   │ Export   │              │
│   │  Resume  │   │ & Score │   │ Results  │              │
│   │  PDF/Doc │   │ Report  │   │ PDF/DOCX │              │
│   └─────────┘   └─────────┘   └─────────┘              │
│   Step 1          Step 2         Step 3                  │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  Features:                                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│  │ 6-Agent AI   │ │ ATS Keyword  │ │ Interview    │     │
│  │ Pipeline     │ │ Alignment    │ │ Preparation  │     │
│  └──────────────┘ └──────────────┘ └──────────────┘     │
│  ┌──────────────┐                                        │
│  │ Quality      │                                        │
│  │ Scoring      │                                        │
│  └──────────────┘                                        │
├──────────────────────────────────────────────────────────┤
│  [Footer]  Resume Intel | Built by Neel & Team           │
└──────────────────────────────────────────────────────────┘
```

---

### 10.3 OptimizePage Layout (Current — already working)

```
┌──────────────────────────────────────────────────────────┐
│  [Navbar]                                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Optimize Resume                                         │
│  Import or paste your resume, add the target JD...       │
│                                                          │
│  [Error banner if any]                                   │
│                                                          │
│  ┌────────────────────┐  ┌────────────────────┐         │
│  │ [Paste Text | PDF] │  │ Job Description    │         │
│  │ ─────────────────  │  │                    │         │
│  │                    │  │                    │         │
│  │  Resume textarea   │  │  JD textarea       │         │
│  │  OR                │  │                    │         │
│  │  PdfUploadZone     │  │                    │         │
│  │                    │  │                    │         │
│  │  X characters      │  │  X characters      │         │
│  └────────────────────┘  └────────────────────┘         │
│                                                          │
│  [ Optimize Resume ]  "Paste your resume to start"       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### 10.4 ResultsPage Layout

```
┌──────────────────────────────────────────────────────────┐
│  [Navbar]                                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Optimization Results         [← New Optimization]       │
│                                                          │
│  ── WHILE LOADING ──────────────────────────────────     │
│  │         ◌ Running optimization pipeline...     │     │
│  ────────────────────────────────────────────────────     │
│                                                          │
│  ── WHEN COMPLETE ──────────────────────────────────     │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │   72%    │ │   78%    │ │    6     │                │
│  │ JD Align │ │ Quality  │ │ Agents   │                │
│  └──────────┘ └──────────┘ └──────────┘                │
│                                                          │
│  ┌ Pipeline Scores ─────────────────────────────────┐   │
│  │ [ingestion 85%] [generation 82%] [quality 78%]   │   │
│  │ [weak detection 71%] [tailoring 76%]             │   │
│  │ [interview 80%]                                   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌ Keyword Coverage ────────────────────────────────┐   │  <-- TO BUILD
│  │ Matched: [Python] [microservices] [AWS] [Postgres]│   │
│  │ Missing: [Kubernetes] [CI/CD] [Terraform]         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌ Optimized Resume ────────────────────────────────┐   │
│  │ # John Doe                                        │   │
│  │ ## Experience                                     │   │
│  │ - Architected 12 microservices...                │   │
│  │                                                   │   │
│  │ [Export PDF]  [Export DOCX]                       │   │  <-- TO BUILD
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌ Weaknesses & Gaps ───────────────────────────────┐   │  <-- TO BUILD
│  │ [MAJOR] No container orchestration experience     │   │
│  │ [MINOR] Employment gap Jun-Sep 2023              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌ Improvement Suggestions ─────────────────────────┐   │
│  │ ⚠ Consider adding metrics to education section    │   │
│  │ ⚠ Bullet 3 lacks quantifiable outcome            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌ Interview Preparation ───────────────────────────┐   │  <-- TO ENHANCE
│  │ ┌ Q1: Tell me about system performance...  ─────┐│   │
│  │ │ Category: behavioral | Difficulty: medium      ││   │
│  │ │ Suggested answer: Reference the microservices..││   │
│  │ └───────────────────────────────────────────────┘│   │
│  │ ┌ Q2: How would you design distributed cache? ──┐│   │
│  │ │ ...                                           ││   │
│  │ └───────────────────────────────────────────────┘│   │
│  │                                                   │   │
│  │ [View Full Interview Prep →]                     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  [Footer]                                                │
└──────────────────────────────────────────────────────────┘
```

---

## 11. State Management & Data Flow

### No external state library needed (yet). Use React hooks + prop drilling.

```
App.tsx (Router)
  ├── HomePage         — no state, just links
  ├── OptimizePage     — local state: resumeText, resumeMode, jdText, loading, error
  │   ├── PdfUploadZone  — internal upload state, lifts text via onTextExtracted
  │   └── Button         — receives loading/disabled
  └── ResultsPage      — useJobStatus(jobId) drives everything
      ├── AlignmentGauge — receives score
      ├── ScoreBadge     — receives score + label
      ├── Card           — container
      ├── SuggestionList — receives suggestions[]
      └── [New components receive slices of result]
```

### Data flow for optimization:
```
1. User fills resume + JD on OptimizePage
2. handleOptimize() calls startOptimization(resumeText, jdText)
3. API returns { job_id }
4. navigate(`/results/${jobId}`)
5. ResultsPage mounts, useJobStatus(jobId) starts polling
6. Poll: GET /optimize/{jobId}/status every 2s
7. When status === "completed":
   - Fetch: GET /optimize/{jobId}/result
   - Set result state → UI renders all sections
```

---

## 12. Code Conventions & Patterns

### Component Pattern
Every component MUST follow this pattern:
```tsx
import { motion } from "framer-motion";

/** Props interface — always exported if component is exported */
interface MyComponentProps {
  /** JSDoc for each prop */
  title: string;
  score?: number;
}

/** JSDoc description of the component */
export function MyComponent({ title, score = 0 }: MyComponentProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {/* ... */}
    </motion.div>
  );
}
```

### Rules
1. **Functional components only** — no class components
2. **Named exports** — no default exports
3. **Props interface** — always define, always typed
4. **JSDoc** on every component and every prop
5. **Tailwind only** — no CSS modules, no inline styles (except dynamic values)
6. **All API calls** go through `lib/api.ts` — never call axios directly in components
7. **Loading + error states** for EVERY async operation
8. **Framer Motion** for all transitions and animations
9. **No `any` type** — use `unknown` and narrow, or define proper types
10. **File naming:** PascalCase for components/pages, camelCase for hooks/utils

---

## 13. PDF Import Feature (Already Integrated)

The PDF import feature is **fully working**. Here's how it flows:

```
OptimizePage
  └── Mode Toggle: [Paste Text] | [Import PDF]
        │
        ├── "Paste Text" mode:
        │     └── <textarea> → setResumeText()
        │
        └── "PDF" mode:
              └── <PdfUploadZone onTextExtracted={handlePdfExtracted} />
                    │
                    ├── User drags file OR clicks to browse
                    ├── Validates file type (.pdf, .docx, .doc, .txt)
                    ├── Calls uploadResume(file) → POST /api/v1/resume/upload
                    ├── Backend uses PyPDF2 (PDF) or python-docx (DOCX) to extract text
                    ├── Returns { text, filename, chars }
                    ├── PdfUploadZone calls onTextExtracted(text, filename)
                    └── OptimizePage sets resumeText + resumeFilename
                          │
                          └── "Edit extracted text" link switches to paste mode
                              with extracted text pre-filled for manual editing
```

**Supported formats on backend:**
| Format | Library | Notes |
|--------|---------|-------|
| `.pdf` | PyPDF2 | Text-based PDFs only. Image-based PDFs will fail with "No text extracted" error |
| `.docx` | python-docx | Extracts paragraph text |
| `.doc` | python-docx | Legacy Word (best-effort) |
| `.txt` | Built-in | UTF-8 decoded |

**Max file size:** 5MB (validated on backend)

---

## 14. Components To Build

### 14.1 `Navbar`
```tsx
interface NavbarProps {
  // No props needed — uses react-router for active link detection
}
```
- Fixed/sticky top bar
- Logo text "Resume Intel" (links to `/`)
- Nav links: Home, Optimize, Dashboard (future)
- Active link highlight (blue underline or bg)
- Mobile: hamburger menu

### 14.2 `Footer`
```tsx
interface FooterProps {
  // No props
}
```
- Simple gray bar at bottom
- "Resume Intel | AI-Powered Resume Optimization"
- "Built by Neel & Team"

### 14.3 `ProgressTracker`
```tsx
interface ProgressTrackerProps {
  currentAgent: string;      // e.g., "quality"
  agentIndex: number;        // 0-5
  totalAgents: number;       // 6
  status: "queued" | "running" | "completed" | "failed";
}
```
- Horizontal step indicator showing all 6 agents
- Steps: Ingestion → Generation → Quality → Weakness → Tailoring → Interview
- Completed steps: green checkmark
- Current step: blue pulse animation
- Future steps: gray dot

### 14.4 `KeywordChips`
```tsx
interface KeywordChipsProps {
  matched: string[];         // Keywords found in resume
  missing: string[];         // Keywords in JD but not resume
}
```
- Matched keywords: green chips
- Missing keywords: red/outline chips
- Wrap layout (`flex-wrap`)

### 14.5 `ExportButtons`
```tsx
interface ExportButtonsProps {
  content: string;           // Markdown content to export
  filename?: string;         // Default: "optimized_resume"
}
```
- Two buttons: "Export PDF" and "Export DOCX"
- Calls POST `/export/pdf` or `/export/docx` with `responseType: "blob"`
- Creates download link and triggers click
- Loading state per button
- Error toast on failure

### 14.6 `InterviewCard`
```tsx
interface InterviewCardProps {
  question: string;
  category: "behavioral" | "technical" | "situational" | "gap_explanation";
  difficulty: "easy" | "medium" | "hard";
  suggestedAnswer: string;
  relevantSection?: string;
}
```
- Expandable card (click to show/hide answer)
- Category badge (colored)
- Difficulty badge
- Animated expand/collapse

### 14.7 `WeaknessCard`
```tsx
interface WeaknessCardProps {
  category: string;
  severity: "critical" | "major" | "minor";
  description: string;
  suggestion: string;
  location?: string;
}
```
- Severity badge: critical=red, major=orange, minor=yellow
- Description + actionable suggestion

### 14.8 `ResumePreview` (Enhancement)
```tsx
interface ResumePreviewProps {
  original: string;
  optimized: string;
}
```
- Side-by-side or tabbed view
- Original (left/tab1) vs Optimized (right/tab2)
- Markdown rendering with section headers

### 14.9 `EmptyState`
```tsx
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: { label: string; href: string };
}
```
- Centered icon + text + optional CTA button
- Use for empty dashboard, no results, etc.

---

## 15. TypeScript Types & Interfaces

Create `frontend/src/lib/types.ts`:

```typescript
// ── API Response wrapper ──
export interface ApiResponse<T = unknown> {
  status: "ok" | "error";
  data: T;
  meta?: Record<string, unknown>;
}

export interface ApiError {
  status: "error";
  error: {
    code: string;
    message: string;
  };
}

// ── Resume Upload ──
export interface ResumeUploadData {
  text: string;
  filename: string;
  chars: number;
}

// ── Optimization ──
export interface OptimizeRequestPayload {
  resume_text: string;
  job_description: string;
  options?: OptimizeOptions;
}

export interface OptimizeOptions {
  skip_interview_prep?: boolean;
  quality_threshold?: number;   // 0.0-1.0
  max_retries?: number;         // 1-5
}

export interface OptimizeStartData {
  job_id: string;
  message: string;
}

// ── Job Status ──
export type JobStatus = "idle" | "queued" | "running" | "completed" | "failed";

export interface JobStatusData {
  job_id: string;
  job_status: JobStatus;
  current_agent?: string;
  progress_percent?: number;
}

// ── Agent Results ──
export interface AgentResult {
  content: string;
  quality_score: number;
  suggestions: string[];
  metadata: Record<string, unknown>;
}

export interface PipelineResults {
  ingestion?: AgentResult;
  generation?: AgentResult;
  quality?: AgentResult;
  weak_detection?: AgentResult;
  tailoring?: AgentResult & {
    metadata: {
      alignment_score?: number;
      matched_keywords?: string[];
      missing_keywords?: string[];
    };
  };
  interview?: AgentResult;
}

export interface OptimizationResultData {
  status: string;
  results: PipelineResults;
}

// ── Alignment ──
export interface AlignmentScoreData {
  overall_score: number;
  gaps: string[];
  section_scores: Record<string, number>;
}

// ── Export ──
export interface ExportRequest {
  content: string;
  filename?: string;
}

// ── Weakness (parsed from agent output) ──
export interface Weakness {
  category: string;
  severity: "critical" | "major" | "minor";
  location?: string;
  description: string;
  suggestion: string;
}

// ── Interview Question (parsed from agent output) ──
export interface InterviewQuestion {
  question: string;
  category: "behavioral" | "technical" | "situational" | "gap_explanation";
  difficulty: "easy" | "medium" | "hard";
  suggested_answer_outline: string;
  relevant_resume_section?: string;
}

export interface TalkingPoint {
  topic: string;
  key_points: string[];
  supporting_evidence?: string;
}
```

---

## 16. Error Handling Patterns

### API Error Handling
```tsx
// In hooks or page-level handlers:
try {
  const data = await someApiCall();
  // handle success
} catch (err: unknown) {
  if (axios.isAxiosError(err)) {
    const apiError = err.response?.data as ApiError;
    const code = apiError?.error?.code || "UNKNOWN";
    const message = apiError?.error?.message || "Something went wrong";

    // Handle specific codes
    if (code === "RATE_LIMIT_EXCEEDED") {
      setError("Too many requests. Please wait a moment.");
    } else if (code === "PARSE_FAILED") {
      setError("Could not extract text from this file. Try a different format.");
    } else {
      setError(message);
    }
  } else {
    setError("Network error. Please check your connection.");
  }
}
```

### UI Error Display
- **Inline errors:** Red banner at top of form (like OptimizePage already does)
- **Toast notifications:** For export success/failure (install `react-hot-toast` or `sonner`)
- **Empty states:** When no data available
- **Retry actions:** Always provide a way to retry

---

## 17. Animation & Motion Guidelines

Using `framer-motion` throughout. Keep animations **subtle and fast**.

### Standard Animations
```tsx
// Page/section entrance
initial={{ opacity: 0, y: 8 }}
animate={{ opacity: 1, y: 0 }}
transition={{ duration: 0.2 }}

// Card entrance
initial={{ opacity: 0, y: 8 }}
animate={{ opacity: 1, y: 0 }}
transition={{ duration: 0.2 }}

// List item stagger
initial={{ opacity: 0, x: -8 }}
animate={{ opacity: 1, x: 0 }}
transition={{ delay: index * 0.05 }}

// Score number entrance
initial={{ opacity: 0, scale: 0.8 }}
animate={{ opacity: 1, scale: 1 }}
transition={{ type: "spring", stiffness: 200 }}

// Button press
whileTap={{ scale: 0.97 }}

// Mode switch (left/right slide)
initial={{ opacity: 0, x: -8 }}  // or x: 8 for opposite direction
animate={{ opacity: 1, x: 0 }}
exit={{ opacity: 0, x: -8 }}
transition={{ duration: 0.15 }}

// Loading spinner
animate={{ rotate: 360 }}
transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
```

### Rules
- Max transition duration: 0.3s for UI elements
- Use `AnimatePresence` for mount/unmount animations
- Use `mode="wait"` on AnimatePresence for sequential transitions
- Spring animations for scores/numbers
- No animation on scroll (keep it simple)

---

## 18. Responsive Design Breakpoints

Using Tailwind's default breakpoints:

| Breakpoint | Min width | Usage |
|------------|-----------|-------|
| `sm:` | 640px | 2-column score grid |
| `md:` | 768px | 2-column resume+JD layout |
| `lg:` | 1024px | Max content width, sidebar |
| `xl:` | 1280px | Extended content |

### Layout Rules
- **Mobile first** — base classes are mobile, add breakpoint prefixes to scale up
- **OptimizePage:** Single column on mobile → 2 columns (`md:grid-cols-2`) on desktop
- **ResultsPage scores:** Single column → 3 columns (`sm:grid-cols-3`)
- **Max width:** `max-w-4xl` for forms, `max-w-5xl` for results
- **Page padding:** `px-4` on all, `py-12` for sections

---

## 19. Accessibility Requirements

- All interactive elements must be keyboard-accessible
- `aria-label` on icon-only buttons
- File input has `aria-label="Upload resume file"` (already done in PdfUploadZone)
- Color is never the only indicator — always pair with text/icon
- Focus rings on inputs (`focus:ring-1 focus:ring-blue-500`)
- Semantic HTML: `<main>`, `<nav>`, `<section>`, `<h1>`-`<h3>` hierarchy
- Alt text on any images
- Screen reader text for loading states

---

## 20. Git Workflow

### Branch Strategy
```
main                    ← production-ready code
├── feat/frontend-*     ← your feature branches
├── feat/ai-*           ← Neel's AI/backend branches
└── feat/rag-*          ← Neel's RAG branches
```

### Your Workflow
1. Pull latest `main`
2. Create feature branch: `git checkout -b feat/frontend-homepage`
3. Work in `frontend/` directory ONLY
4. Commit with clear messages: `feat(frontend): build homepage hero section`
5. Push and create PR → Neel reviews
6. After merge, pull main and branch again

### Files You Own (your domain)
```
frontend/src/components/*     ← ALL components
frontend/src/pages/*          ← ALL pages
frontend/src/hooks/*          ← ALL hooks
frontend/src/lib/types.ts     ← shared types
frontend/src/lib/utils.ts     ← utility functions
frontend/src/lib/constants.ts ← app constants
frontend/src/App.tsx          ← routing changes
frontend/public/*             ← static assets
frontend/index.html           ← HTML shell
```

### Files Neel Owns (don't modify)
```
frontend/src/lib/api.ts       ← API client (Neel maintains to match backend)
frontend/vite.config.ts       ← Build config
frontend/package.json          ← Only add deps, don't change scripts
src/**                         ← Entire backend
docs/**                        ← Architecture docs
```

### Shared (coordinate before changing)
```
frontend/tailwind.config.js    ← theme customization
frontend/tsconfig.json         ← TypeScript config
```

---

## 21. Testing

### Component Testing (setup when ready)
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

### Test file pattern
```
frontend/src/components/__tests__/Button.test.tsx
frontend/src/pages/__tests__/HomePage.test.tsx
```

### Test pattern
```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Button } from "../Button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("shows spinner when loading", () => {
    render(<Button loading>Click me</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

---

## Quick Reference — What To Build (Priority Order)

| Priority | Task | Files |
|----------|------|-------|
| P0 | Create `lib/types.ts` with all TypeScript interfaces | `lib/types.ts` |
| P0 | Build `Navbar` component | `components/Navbar.tsx` |
| P0 | Redesign `HomePage` with hero + features + how-it-works | `pages/HomePage.tsx` |
| P1 | Build `ExportButtons` component + `useExport` hook | `components/ExportButtons.tsx`, `hooks/useExport.ts` |
| P1 | Build `KeywordChips` for matched/missing keywords | `components/KeywordChips.tsx` |
| P1 | Enhance `ResultsPage` with keywords, export, weakness cards | `pages/ResultsPage.tsx` |
| P1 | Build `WeaknessCard` component | `components/WeaknessCard.tsx` |
| P2 | Build `InterviewCard` with expandable Q&A | `components/InterviewCard.tsx` |
| P2 | Build `ProgressTracker` for pipeline status | `components/ProgressTracker.tsx` |
| P2 | Build `Footer` component | `components/Footer.tsx` |
| P3 | Build `ResumePreview` (side-by-side view) | `components/ResumePreview.tsx` |
| P3 | Build `DashboardPage` | `pages/DashboardPage.tsx` |
| P3 | Build `InterviewPrepPage` (full-page view) | `pages/InterviewPrepPage.tsx` |
| P3 | Add `useAlignment` hook for standalone scoring | `hooks/useAlignment.ts` |

---

**Questions?** Reach out to Neel for any backend/API clarifications. The backend is running and all endpoints listed above are functional.
