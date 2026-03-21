# API Layer

## Route Pattern
- All routes in src/api/routes/
- Pydantic models in src/api/schemas/
- Use dependency injection for services
- Async handlers, background tasks via Celery for optimization pipeline

## Response Format
All responses: {"status": "ok"|"error", "data": {...}, "meta": {...}}
Errors: {"status": "error", "error": {"code": "...", "message": "..."}}
