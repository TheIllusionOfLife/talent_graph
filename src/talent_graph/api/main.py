"""FastAPI application factory with structured logging."""

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from talent_graph.api.routes import admin, health
from talent_graph.config.settings import get_settings
from talent_graph.graph.neo4j_client import close_driver, run_query
from talent_graph.graph.queries import CONSTRAINTS


def _configure_logging(log_format: str, log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
            foreign_pre_chain=shared_processors,
        )
    )
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_format, settings.log_level)

    log = structlog.get_logger()

    app = FastAPI(
        title="Talent Graph API",
        description="Talent Discovery using knowledge graphs and embeddings",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(admin.router)

    @app.on_event("startup")
    async def startup() -> None:
        log.info("app.startup")
        # Ensure Neo4j uniqueness constraints exist
        try:
            for constraint in CONSTRAINTS:
                await run_query(constraint)
            log.info("neo4j.constraints.ok")
        except Exception as exc:
            log.warning("neo4j.constraints.failed", error=str(exc))

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await close_driver()
        log.info("app.shutdown")

    return app
