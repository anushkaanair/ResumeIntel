---
name: api-endpoint
description: Create FastAPI endpoints for the resume intelligence API. Use when adding new routes, creating Pydantic schemas, or building API handlers. Triggers on "new endpoint", "add route", "API for", "create endpoint".
---

# API Endpoint Builder

## Route Pattern

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from src.api.schemas.resume import OptimizeRequest, OptimizeResponse
from src.api.deps import get_pipeline_service

router = APIRouter(prefix="/api/v1", tags=["optimize"])

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    request: OptimizeRequest,
    background_tasks: BackgroundTasks,
    service = Depends(get_pipeline_service),
):
    """Run full optimization pipeline on resume."""
    job_id = await service.start_optimization(request)
    return OptimizeResponse(status="ok", data={"job_id": job_id, "message": "Pipeline started"})
```

## Schema Pattern

```python
from pydantic import BaseModel, Field

class OptimizeRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, description="Resume content")
    job_description: str = Field(..., min_length=20, description="Target JD")
    options: OptimizeOptions | None = None

class OptimizeResponse(BaseModel):
    status: str
    data: dict
    meta: dict | None = None
```

## Rules
- Always use Pydantic models — no raw dicts
- Async handlers for all routes
- Heavy work -> Celery background tasks
- Response format: {"status", "data", "meta"}
- Add route to src/api/__init__.py router includes
