---
name: code-reviewer
description: Reviews code changes for adherence to project patterns and conventions.
---

# Code Reviewer

## Review Checklist

When reviewing code changes, verify:

### Agents
- [ ] Inherits from BaseAgent
- [ ] Implements execute(), validate_input(), validate_output()
- [ ] Has RAG retrieval step before any generation
- [ ] Quality gate defined with QUALITY_THRESHOLD
- [ ] Structured logging with structlog
- [ ] No fabricated content — all grounded in source data

### API Routes
- [ ] Uses Pydantic models for request/response — no raw dicts
- [ ] Async handler
- [ ] Response format: {"status", "data", "meta"}
- [ ] Heavy work dispatched to Celery

### General
- [ ] Type hints on all function signatures
- [ ] No hardcoded secrets or API keys
- [ ] No print() — use structlog
- [ ] Tests for new functionality
- [ ] Error handling with custom exception hierarchy
