"""FastAPI application entry point."""
from __future__ import annotations

import logging

import structlog

from src.api import app

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)


@app.on_event("startup")
async def startup() -> None:
    log = structlog.get_logger()
    log.info("app.startup", version="0.1.0")


@app.on_event("shutdown")
async def shutdown() -> None:
    log = structlog.get_logger()
    log.info("app.shutdown")
