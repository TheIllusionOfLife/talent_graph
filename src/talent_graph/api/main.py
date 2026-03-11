"""FastAPI application factory with structured logging."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
import structlog.types
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request as StarletteRequest

from talent_graph.api.limiter import limiter
from talent_graph.api.routes import admin, health
from talent_graph.api.routes.discovery import router as discovery_router
from talent_graph.api.routes.graph import router as graph_router
from talent_graph.api.routes.lookalike import router as lookalike_router
from talent_graph.api.routes.person import router as person_router
from talent_graph.api.routes.search import router as search_router
from talent_graph.api.routes.searches import router as searches_router
from talent_graph.api.routes.shortlist import router as shortlist_router
from talent_graph.config.settings import get_settings
from talent_graph.features.person_features import init_prestige_names
from talent_graph.graph.neo4j_client import close_driver, run_write_query
from talent_graph.graph.queries import CONSTRAINTS


async def _rate_limit_handler(_request: StarletteRequest, exc: RateLimitExceeded) -> JSONResponse:
    raw = getattr(exc, "retry_after", None)
    retry_after = str(raw) if raw else "60"
    return JSONResponse(
        {"detail": f"Rate limit exceeded: {exc.detail}"},
        status_code=429,
        headers={"Retry-After": retry_after},
    )


def _configure_logging(log_format: str, log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
            foreign_pre_chain=shared_processors,
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_format, settings.log_level)
    log = structlog.get_logger()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:  # noqa: ANN001
        _DEFAULT = "change-me-in-production"
        if settings.environment == "production":
            api_blank = not settings.api_key.strip()
            secret_blank = not settings.app_secret.strip()
            if (
                settings.api_key == _DEFAULT
                or settings.app_secret == _DEFAULT
                or api_blank
                or secret_blank
            ):
                raise RuntimeError(
                    "Refusing to start: default or blank API_KEY/APP_SECRET in production. "
                    "Set real values via environment variables."
                )
        else:
            if settings.api_key == _DEFAULT:
                log.warning(
                    "api.insecure_default_key", hint="Set API_KEY env var before deployment"
                )
            if settings.app_secret == _DEFAULT:
                log.warning(
                    "api.insecure_default_secret",
                    hint="Set APP_SECRET env var — owner_hash isolation is broken with this placeholder",
                )
        log.info("app.startup")
        try:
            for constraint in CONSTRAINTS:
                await run_write_query(constraint)
            log.info("neo4j.constraints.ok")
        except Exception as exc:
            log.warning("neo4j.constraints.failed", error=str(exc))
        loaded_from_db = await init_prestige_names()
        log.info("prestige_orgs.loaded", source="db" if loaded_from_db else "fallback")
        yield
        await close_driver()
        log.info("app.shutdown")

    app = FastAPI(
        title="Talent Graph API",
        description="Talent Discovery using knowledge graphs and embeddings",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(admin.router)
    app.include_router(search_router)
    app.include_router(person_router)
    app.include_router(discovery_router)
    app.include_router(graph_router)
    app.include_router(lookalike_router)
    app.include_router(shortlist_router)
    app.include_router(searches_router)

    return app
