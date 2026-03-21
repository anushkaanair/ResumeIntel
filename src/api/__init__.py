"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import resume, optimize, export


def create_app() -> FastAPI:
    app = FastAPI(
        title="Resume Intelligence API",
        description="AI-powered multi-agent resume optimization system",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(resume.router, prefix="/api/v1", tags=["resume"])
    app.include_router(optimize.router, prefix="/api/v1", tags=["optimize"])
    app.include_router(export.router, prefix="/api/v1", tags=["export"])

    return app


app = create_app()
