# Agent Pipeline Specification

## Overview

The system uses six specialized AI agents arranged in a sequential pipeline. Each agent has a single responsibility, well-defined input/output types, quality gates, and retry behavior. The pipeline executes as a background task and reports progress through Redis-backed job status.

## Pipeline Order

```
IngestionAgent → GenerationAgent → QualityAgent → WeakDetectionAgent → TailoringAgent → InterviewAgent
```

## Common Agent Interface

All agents implement the `BaseAgent` abstract class:

```python
class BaseAgent(ABC):
    name: str
    max_retries: int = 3
    backoff_strategy: str = "exponential"  # 1s, 2s, 4s

    @abstractmethod
    async def execute(self, input: AgentInput) -> AgentOutput:
        """Core agent logic."""
        ...

    @abstractmethod
    async def validate(self, output: AgentOutput) -> ValidationResult:
        """Validate output meets quality thresholds."""
        ...

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute with retry logic and validation."""
        for attempt in range(self.max_retries + 1):
            output = await self.execute(input)
            result = await self.validate(output)
            if result.passed:
                return output
            if attempt < self.max_retries:
                await asyncio.sleep(2 ** attempt)  # exponential backoff
        raise AgentRetryExhaustedError(self.name, result.reason)
```

---

## Agent 1: IngestionAgent

**Purpose:** Parse raw resume text into structured, typed segments.

**Input:**
```python
class IngestionInput:
    raw_text: str              # Extracted text from PDF/DOCX
    filename: str              # Original filename for format hints
    metadata: dict             # File metadata (page count, etc.)
```

**Output:**
```python
class IngestionOutput:
    segments: list[ResumeSegment]
    summary: str                    # Brief resume summary
    detected_sections: list[str]    # e.g., ["experience", "education", "skills"]

class ResumeSegment:
    section_type: str     # experience | education | skills | projects | summary | certifications
    content: str          # Raw text of the segment
    bullets: list[str]    # Individual bullet points (for experience/projects)
    position: int         # Order in original document
    metadata: dict        # Additional parsed info (dates, company names, etc.)
```

**Validation:**
- At least 1 segment must be extracted.
- Each segment must have non-empty content.
- `section_type` must be one of the recognized types.

**Behavior:**
- Uses a combination of heuristic rules (section header detection) and LLM-based classification.
- Handles varied resume formats: single-column, two-column, creative layouts.
- Preserves bullet point structure within experience and project sections.

---

## Agent 2: GenerationAgent

**Purpose:** Generate optimized, metrics-driven bullet points for experience and project sections.

**Input:**
```python
class GenerationInput:
    segments: list[ResumeSegment]   # From IngestionAgent
    rag_context: list[str]          # Retrieved context chunks from RAG
    job_description: str | None     # Target JD (if available at this stage)
    style_preferences: dict         # Tone, verbosity, industry norms
```

**Output:**
```python
class GenerationOutput:
    optimized_segments: list[OptimizedSegment]
    generation_metadata: dict       # Token usage, model info

class OptimizedSegment:
    section_type: str
    original_content: str
    optimized_bullets: list[OptimizedBullet]

class OptimizedBullet:
    original: str
    optimized: str
    changes_made: list[str]         # e.g., ["added metric", "stronger action verb"]
    confidence: float               # 0.0 to 1.0
```

**Validation:**
- Every original bullet must have a corresponding optimized version.
- Optimized bullets must start with a strong action verb.
- Confidence score must be >= 0.5 for each bullet.

**Behavior:**
- Uses RAG context to ground generation in the user's actual experience.
- Applies STAR format (Situation, Task, Action, Result) where applicable.
- Injects quantifiable metrics when the original lacks them (with clear indication).
- Preserves factual accuracy; never fabricates experience.

---

## Agent 3: QualityAgent

**Purpose:** Enforce quality standards on generated content. Acts as a gate between generation and downstream agents.

**Input:**
```python
class QualityInput:
    optimized_segments: list[OptimizedSegment]  # From GenerationAgent
    original_segments: list[ResumeSegment]       # For comparison
```

**Output:**
```python
class QualityOutput:
    scored_segments: list[ScoredSegment]
    overall_quality_score: float    # Weighted average across all bullets
    passed: bool                    # True if overall_quality_score >= 0.7

class ScoredSegment:
    section_type: str
    bullets: list[ScoredBullet]

class ScoredBullet:
    text: str
    quality_score: float            # 0.0 to 1.0
    criteria_scores: dict           # Per-criterion breakdown
    issues: list[str]               # Identified problems
    suggestions: list[str]          # Improvement suggestions
```

**Quality Gate Threshold: 0.7**

**Scoring Criteria:**
| Criterion           | Weight | Description                                      |
|---------------------|--------|--------------------------------------------------|
| Action verb strength| 0.15   | Starts with strong, specific action verb          |
| Quantification      | 0.20   | Contains measurable metrics or outcomes           |
| Specificity         | 0.20   | Avoids vague language, names technologies/methods |
| Conciseness         | 0.15   | Appropriate length (15-30 words per bullet)       |
| Relevance           | 0.15   | Relevant to stated role/industry                  |
| Grammar/clarity     | 0.15   | Grammatically correct, clear communication        |

**Validation:**
- `overall_quality_score` must be >= 0.7 to pass.
- If the gate fails, the pipeline sends feedback to GenerationAgent for a retry cycle.

**Behavior:**
- Evaluates each bullet independently against the criteria table.
- Provides actionable feedback for bullets that score below threshold.
- On retry, the QualityAgent receives both the previous attempt and its own feedback.

---

## Agent 4: WeakDetectionAgent

**Purpose:** Identify weak areas, gaps, and improvement opportunities across the entire resume.

**Input:**
```python
class WeakDetectionInput:
    scored_segments: list[ScoredSegment]   # From QualityAgent
    original_segments: list[ResumeSegment] # Original resume data
    job_description: str | None            # Target JD for contextual analysis
```

**Output:**
```python
class WeakDetectionOutput:
    weaknesses: list[Weakness]
    gap_analysis: GapAnalysis
    strength_areas: list[str]

class Weakness:
    location: str               # Section + bullet index
    category: str               # "vague_language" | "missing_metrics" | "passive_voice" |
                                # "outdated_skills" | "gap_in_timeline" | "missing_section"
    severity: str               # "critical" | "major" | "minor"
    description: str            # Human-readable explanation
    suggestion: str             # Recommended fix

class GapAnalysis:
    missing_skills: list[str]           # Skills in JD but not in resume
    underrepresented_areas: list[str]   # Sections that need expansion
    timeline_gaps: list[dict]           # Employment gaps detected
```

**Validation:**
- Output must contain at least a `weaknesses` list (can be empty if resume is strong).
- Each weakness must have a valid `category` and `severity`.
- `gap_analysis` must be present even if all lists are empty.

**Behavior:**
- Analyzes resume holistically, not just individual bullets.
- Cross-references skills mentioned in the JD against resume content.
- Detects employment timeline gaps longer than 3 months.
- Identifies sections commonly expected but missing (e.g., no skills section).

---

## Agent 5: TailoringAgent

**Purpose:** Tailor the optimized resume to a specific job description, maximizing alignment.

**Input:**
```python
class TailoringInput:
    scored_segments: list[ScoredSegment]      # Quality-passed content
    weaknesses: list[Weakness]                 # From WeakDetectionAgent
    gap_analysis: GapAnalysis
    job_description: str                       # Target JD (required)
    rag_context: list[str]                     # Additional retrieved context
```

**Output:**
```python
class TailoringOutput:
    tailored_segments: list[TailoredSegment]
    alignment_score: float          # 0.0 to 1.0
    keyword_coverage: dict          # JD keywords found/missing in resume
    reordering_suggestions: list[str]  # Suggested section reordering

class TailoredSegment:
    section_type: str
    bullets: list[TailoredBullet]

class TailoredBullet:
    text: str
    alignment_delta: float          # How much alignment improved vs. pre-tailoring
    matched_jd_keywords: list[str]  # JD keywords this bullet addresses
```

**Quality Gate Threshold: 0.6 (alignment score)**

**Validation:**
- `alignment_score` must be >= 0.6.
- Every tailored bullet must map to at least one JD keyword or requirement.
- Tailored content must not introduce fabricated experience.

**Behavior:**
- Maps JD requirements to resume sections.
- Rewords bullets to incorporate JD terminology naturally.
- Suggests reordering sections to put most relevant content first.
- Addresses gaps identified by WeakDetectionAgent where possible.

---

## Agent 6: InterviewAgent

**Purpose:** Generate interview preparation materials based on the tailored resume and job description.

**Input:**
```python
class InterviewInput:
    tailored_segments: list[TailoredSegment]   # From TailoringAgent
    job_description: str
    gap_analysis: GapAnalysis
    weaknesses: list[Weakness]
```

**Output:**
```python
class InterviewOutput:
    questions: list[InterviewQuestion]
    talking_points: list[TalkingPoint]
    preparation_summary: str

class InterviewQuestion:
    question: str
    category: str               # "behavioral" | "technical" | "situational" | "gap_explanation"
    difficulty: str             # "easy" | "medium" | "hard"
    suggested_answer_outline: str
    relevant_resume_section: str

class TalkingPoint:
    topic: str
    key_points: list[str]
    supporting_evidence: str    # Reference to specific resume content
```

**Validation:**
- Must generate at least 5 questions.
- Questions must cover at least 2 different categories.
- Each question must have a non-empty `suggested_answer_outline`.

**Behavior:**
- Generates questions likely to be asked based on the JD requirements.
- Creates "gap explanation" questions for any weaknesses or timeline gaps.
- Provides STAR-formatted answer outlines referencing actual resume content.
- Covers both behavioral and technical dimensions.

---

## Retry Behavior

All agents share the same retry policy:

| Parameter         | Value        |
|-------------------|-------------|
| Max retries       | 3           |
| Backoff strategy  | Exponential  |
| Base delay        | 1 second     |
| Delay sequence    | 1s, 2s, 4s  |
| Retry trigger     | Validation failure or transient error |
| Non-retryable     | Input schema errors, authentication failures |

When a quality gate fails (QualityAgent or TailoringAgent), the retry feeds the validation feedback back into the preceding generation step, allowing the LLM to self-correct.

## Pipeline Composition and Execution

```python
pipeline = Pipeline(
    agents=[
        IngestionAgent(),
        GenerationAgent(),
        QualityAgent(),
        WeakDetectionAgent(),
        TailoringAgent(),
        InterviewAgent(),
    ],
    on_agent_complete=update_job_progress,   # Callback for status updates
    on_pipeline_fail=mark_job_failed,        # Callback for failure handling
)

# Execution
result = await pipeline.run(
    initial_input=IngestionInput(raw_text=text, filename=name, metadata=meta),
    context={"job_description": jd_text, "user_id": user_id},
)
```

Pipeline progress is reported per-agent, allowing the frontend to show a step-by-step progress indicator (e.g., "Step 3/6: Quality check...").
