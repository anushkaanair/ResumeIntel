"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.security import ApiKeyMiddleware
from src.config.settings import settings
from src.api.routes import resume, optimize, export, canvas, interview, jd, ws, auth


def create_app() -> FastAPI:
    app = FastAPI(
        title="Resume Intelligence API",
        description="AI-powered multi-agent resume optimization system",
        version="0.2.0",
    )

    app.add_middleware(ApiKeyMiddleware)
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # V1 routes (existing)
    app.include_router(resume.router, prefix="/api/v1", tags=["resume"])
    app.include_router(optimize.router, prefix="/api/v1", tags=["optimize"])
    app.include_router(export.router, prefix="/api/v1", tags=["export"])

    # V2 routes (Canvas, Interview, JD)
    app.include_router(canvas.router, prefix="/api/v1", tags=["canvas"])
    app.include_router(interview.router, prefix="/api/v1", tags=["interview"])
    app.include_router(jd.router, prefix="/api/v1", tags=["jd"])

    # OAuth (LinkedIn live profile sync)
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])

    # WebSocket (no prefix — uses /ws/optimize/{jobId})
    app.include_router(ws.router, tags=["websocket"])

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {
            "status": "ok",
            "auth_required": bool(settings.api_secret_key),
            "llm_provider": settings.llm_provider,
            "llm_configured": settings.llm_provider != "openai" or bool(settings.openai_api_key),
        }

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built React app from the same origin (one URL / one tunnel for the whole product)."""
    from pathlib import Path

    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    dist = Path(settings.frontend_dist).resolve()
    index = dist / "index.html"
    if not index.is_file():
        return

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith(("api/", "ws/")):
            raise HTTPException(status_code=404)
        target = (dist / path).resolve()
        if path and target.is_file() and dist in target.parents:
            return FileResponse(target)
        return FileResponse(index)


app = create_app()
