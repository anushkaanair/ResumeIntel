"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import resume, optimize, export, canvas, interview, jd, ws


def create_app() -> FastAPI:
    app = FastAPI(
        title="Resume Intelligence API",
        description="AI-powered multi-agent resume optimization system",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
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

    # WebSocket (no prefix — uses /ws/optimize/{jobId})
    app.include_router(ws.router, tags=["websocket"])

    return app


app = create_app()
