# API Design

## Overview

The API layer is built with FastAPI (Python 3.11+) and follows REST conventions. All endpoints are versioned under `/api/v1/`. Authentication uses JWT bearer tokens. Background processing is used for long-running optimization pipelines, with status polling endpoints for progress tracking.

**Base URL:** `https://api.resume-intel.dev/api/v1`

## Authentication

All endpoints except `/auth/register` and `/auth/login` require a valid JWT bearer token.

**Token format:** JWT with HS256 signing

| Property        | Value            |
|-----------------|------------------|
| Algorithm       | HS256            |
| Access token TTL | 30 minutes      |
| Refresh token TTL| 7 days          |
| Token location  | `Authorization: Bearer <token>` header |

**Auth endpoints (not detailed here):**
- `POST /api/v1/auth/register` -- Create account
- `POST /api/v1/auth/login` -- Obtain tokens
- `POST /api/v1/auth/refresh` -- Refresh access token

---

## Endpoints

### 1. Upload Resume

**`POST /api/v1/resume/upload`**

Upload a resume file (PDF or DOCX) for parsing and indexing.

**Request:**
- Content-Type: `multipart/form-data`
- Body:

| Field  | Type   | Required | Description              |
|--------|--------|----------|--------------------------|
| file   | File   | Yes      | PDF or DOCX file (max 5MB) |

**Response: `201 Created`**
```json
{
  "resume_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "john_doe_resume.pdf",
  "sections_detected": ["summary", "experience", "education", "skills"],
  "segment_count": 24,
  "parsed_at": "2026-03-21T10:30:00Z"
}
```

**Error responses:**
| Status | Code                  | Description                        |
|--------|-----------------------|------------------------------------|
| 400    | INVALID_FILE_TYPE     | File is not PDF or DOCX            |
| 400    | FILE_TOO_LARGE        | File exceeds 5MB limit             |
| 400    | PARSE_FAILED          | Could not extract text from file   |
| 401    | UNAUTHORIZED          | Missing or invalid JWT             |
| 429    | RATE_LIMIT_EXCEEDED   | Too many requests                  |

---

### 2. Run Optimization Pipeline

**`POST /api/v1/optimize`**

Start an asynchronous optimization pipeline for a resume against a job description. Returns a job ID for status polling.

**Request:**
```json
{
  "resume_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_description": "We are looking for a Senior Backend Engineer...",
  "job_title": "Senior Backend Engineer",
  "company": "Acme Corp",
  "options": {
    "include_interview_prep": true,
    "style": "professional",
    "verbosity": "concise"
  }
}
```

| Field              | Type    | Required | Description                           |
|--------------------|---------|----------|---------------------------------------|
| resume_id          | UUID    | Yes      | ID from upload response               |
| job_description    | string  | Yes      | Full job description text             |
| job_title          | string  | No       | Target job title                      |
| company            | string  | No       | Target company name                   |
| options            | object  | No       | Pipeline configuration                |
| options.include_interview_prep | bool | No | Generate interview prep (default: true) |
| options.style      | string  | No       | "professional" or "creative" (default: "professional") |
| options.verbosity  | string  | No       | "concise" or "detailed" (default: "concise") |

**Response: `202 Accepted`**
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "PENDING",
  "estimated_duration_seconds": 45,
  "status_url": "/api/v1/optimize/660e8400-e29b-41d4-a716-446655440001/status"
}
```

**Error responses:**
| Status | Code                  | Description                          |
|--------|-----------------------|--------------------------------------|
| 400    | INVALID_RESUME_ID     | Resume ID not found                  |
| 400    | EMPTY_JOB_DESCRIPTION | Job description is empty or too short|
| 401    | UNAUTHORIZED          | Missing or invalid JWT               |
| 403    | FORBIDDEN             | Resume belongs to another user       |
| 429    | RATE_LIMIT_EXCEEDED   | Too many optimization requests       |

---

### 3. Check Optimization Status

**`GET /api/v1/optimize/{job_id}/status`**

Poll for the current status of an optimization run.

**Path parameters:**
| Parameter | Type | Description             |
|-----------|------|-------------------------|
| job_id    | UUID | Optimization job ID     |

**Response: `200 OK`**
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "RUNNING",
  "current_agent": "QualityAgent",
  "agent_index": 3,
  "total_agents": 6,
  "progress_percent": 50,
  "started_at": "2026-03-21T10:31:00Z",
  "elapsed_seconds": 18
}
```

**Status values:**
| Status      | Description                                    |
|-------------|------------------------------------------------|
| PENDING     | Queued, not yet started                        |
| RUNNING     | Pipeline is executing (see `current_agent`)    |
| COMPLETED   | All agents finished successfully               |
| FAILED      | Pipeline failed (see result endpoint for error)|

**Error responses:**
| Status | Code              | Description                    |
|--------|-------------------|--------------------------------|
| 401    | UNAUTHORIZED      | Missing or invalid JWT         |
| 403    | FORBIDDEN         | Job belongs to another user    |
| 404    | JOB_NOT_FOUND     | No job with this ID            |

---

### 4. Get Optimization Result

**`GET /api/v1/optimize/{job_id}/result`**

Retrieve the full result of a completed optimization run.

**Path parameters:**
| Parameter | Type | Description             |
|-----------|------|-------------------------|
| job_id    | UUID | Optimization job ID     |

**Response: `200 OK`**
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "COMPLETED",
  "quality_score": 0.84,
  "alignment_score": 0.72,
  "optimized_resume": {
    "sections": [
      {
        "section_type": "experience",
        "bullets": [
          {
            "original": "Worked on backend services",
            "optimized": "Architected and deployed 12 microservices handling 50K RPM, reducing API latency by 35% through caching and query optimization",
            "quality_score": 0.91,
            "matched_keywords": ["microservices", "API", "optimization"]
          }
        ]
      }
    ]
  },
  "weaknesses": [
    {
      "category": "missing_metrics",
      "severity": "major",
      "location": "experience.bullet[3]",
      "description": "Bullet lacks quantifiable outcomes",
      "suggestion": "Add metrics such as percentage improvement or user count"
    }
  ],
  "keyword_coverage": {
    "matched": ["Python", "microservices", "AWS", "PostgreSQL"],
    "missing": ["Kubernetes", "CI/CD", "Terraform"]
  },
  "interview_prep": {
    "questions": [
      {
        "question": "Tell me about a time you optimized system performance.",
        "category": "behavioral",
        "difficulty": "medium",
        "suggested_answer_outline": "Reference the microservices optimization project. Use STAR format: Situation (high latency), Task (improve performance), Action (caching + query optimization), Result (35% latency reduction)."
      }
    ],
    "talking_points": [
      {
        "topic": "Backend Architecture Experience",
        "key_points": ["12 microservices at scale", "50K RPM traffic handling", "Performance optimization expertise"]
      }
    ]
  },
  "completed_at": "2026-03-21T10:31:42Z"
}
```

**Error responses:**
| Status | Code              | Description                        |
|--------|-------------------|------------------------------------|
| 401    | UNAUTHORIZED      | Missing or invalid JWT             |
| 403    | FORBIDDEN         | Job belongs to another user        |
| 404    | JOB_NOT_FOUND     | No job with this ID                |
| 409    | JOB_NOT_COMPLETE  | Job is still PENDING or RUNNING    |

---

### 5. Get Alignment Score

**`POST /api/v1/alignment/score`**

Calculate alignment between a resume and a job description without running the full pipeline.

**Request:**
```json
{
  "resume_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_description": "We are looking for a Senior Backend Engineer..."
}
```

| Field            | Type   | Required | Description                  |
|------------------|--------|----------|------------------------------|
| resume_id        | UUID   | Yes      | Resume to score              |
| job_description  | string | Yes      | JD to align against          |

**Response: `200 OK`**
```json
{
  "alignment_score": 0.68,
  "keyword_coverage": {
    "matched": ["Python", "microservices", "AWS"],
    "missing": ["Kubernetes", "Terraform"],
    "match_rate": 0.6
  },
  "section_scores": {
    "experience": 0.74,
    "skills": 0.65,
    "education": 0.58,
    "projects": 0.71
  },
  "top_gaps": [
    "No mention of container orchestration (Kubernetes)",
    "Infrastructure-as-code experience not evident"
  ]
}
```

**Error responses:**
| Status | Code                  | Description                          |
|--------|-----------------------|--------------------------------------|
| 400    | INVALID_RESUME_ID     | Resume ID not found                  |
| 400    | EMPTY_JOB_DESCRIPTION | Job description is empty             |
| 401    | UNAUTHORIZED          | Missing or invalid JWT               |
| 403    | FORBIDDEN             | Resume belongs to another user       |

---

### 6. Generate Interview Prep

**`POST /api/v1/interview/prep`**

Generate interview preparation materials standalone (without running the full optimization pipeline).

**Request:**
```json
{
  "resume_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_description": "We are looking for a Senior Backend Engineer...",
  "focus_areas": ["behavioral", "technical"],
  "question_count": 10
}
```

| Field            | Type       | Required | Description                          |
|------------------|------------|----------|--------------------------------------|
| resume_id        | UUID       | Yes      | Resume to base prep on               |
| job_description  | string     | Yes      | Target JD                            |
| focus_areas      | string[]   | No       | Categories to focus on (default: all)|
| question_count   | integer    | No       | Number of questions (default: 10, max: 25) |

**Response: `200 OK`**
```json
{
  "questions": [
    {
      "question": "Describe your experience designing distributed systems.",
      "category": "technical",
      "difficulty": "hard",
      "suggested_answer_outline": "Draw on microservices architecture experience. Discuss trade-offs between consistency and availability, specific technologies used, and scale metrics.",
      "relevant_resume_section": "experience"
    }
  ],
  "talking_points": [
    {
      "topic": "System Design Philosophy",
      "key_points": [
        "Event-driven microservices architecture",
        "Performance optimization track record",
        "Data-driven decision making"
      ],
      "supporting_evidence": "Designed 12 microservices handling 50K RPM"
    }
  ],
  "preparation_summary": "Focus on demonstrating hands-on distributed systems experience and quantifiable performance improvements. Prepare gap explanations for Kubernetes and IaC experience."
}
```

**Error responses:**
| Status | Code                  | Description                          |
|--------|-----------------------|--------------------------------------|
| 400    | INVALID_RESUME_ID     | Resume ID not found                  |
| 400    | EMPTY_JOB_DESCRIPTION | Job description is empty             |
| 400    | INVALID_QUESTION_COUNT| question_count must be 1-25          |
| 401    | UNAUTHORIZED          | Missing or invalid JWT               |
| 403    | FORBIDDEN             | Resume belongs to another user       |

---

## Rate Limiting

Rate limits are enforced per-user using a sliding window algorithm backed by Redis.

| Endpoint Category       | Limit           | Window   |
|-------------------------|-----------------|----------|
| Optimization (POST /optimize) | 10 requests | 1 minute |
| Read endpoints (GET)    | 60 requests     | 1 minute  |
| Upload (POST /resume/upload) | 20 requests | 1 minute |
| Alignment scoring       | 30 requests     | 1 minute  |
| Interview prep          | 20 requests     | 1 minute  |

**Rate limit headers included in every response:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1711012300
```

When rate limited, the API returns:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 23 seconds.",
    "retry_after": 23
  }
}
```

## Standard Error Format

All errors follow a consistent structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description.",
    "details": {}
  }
}
```

### Error Code Reference

| HTTP Status | Code                    | Description                                |
|-------------|-------------------------|--------------------------------------------|
| 400         | BAD_REQUEST             | Generic malformed request                  |
| 400         | INVALID_FILE_TYPE       | Uploaded file is not PDF or DOCX           |
| 400         | FILE_TOO_LARGE          | File exceeds 5MB limit                     |
| 400         | PARSE_FAILED            | Text extraction from file failed           |
| 400         | INVALID_RESUME_ID       | Referenced resume does not exist           |
| 400         | EMPTY_JOB_DESCRIPTION   | JD is missing or below minimum length      |
| 400         | INVALID_QUESTION_COUNT  | question_count out of valid range          |
| 401         | UNAUTHORIZED            | Missing, expired, or malformed JWT         |
| 403         | FORBIDDEN               | Authenticated but not authorized for resource |
| 404         | NOT_FOUND               | Generic resource not found                 |
| 404         | JOB_NOT_FOUND           | Optimization job ID does not exist         |
| 409         | JOB_NOT_COMPLETE        | Result requested before job finished       |
| 422         | VALIDATION_ERROR        | Request body fails schema validation       |
| 429         | RATE_LIMIT_EXCEEDED     | Too many requests in the time window       |
| 500         | INTERNAL_ERROR          | Unexpected server error                    |
| 503         | SERVICE_UNAVAILABLE     | Downstream service (LLM, FAISS) unreachable|
