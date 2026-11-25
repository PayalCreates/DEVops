"""FastAPI application factory."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.api.routes import analytics, auth, health, tasks, users
from app.core.config import get_settings
from app.core.logging import configure_logging, request_id_ctx
from app.core.metrics import APP_INFO
from app.core.middleware import ObservabilityMiddleware

log = logging.getLogger("app")


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_production_safety()
    configure_logging(settings.log_level, color=settings.app_color)
    APP_INFO.info({"version": settings.app_version, "color": settings.app_color,
                   "environment": settings.environment})

    is_prod = settings.environment == "production"
    app = FastAPI(
        title="DevSecOps360 Task API",
        version=settings.app_version,
        description="Secure task management API with JWT auth and RBAC.",
        # Hide interactive docs in production (reduce attack surface).
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )

    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    api_prefix = "/api/v1"
    for r in (auth.router, users.router, tasks.router, analytics.router):
        app.include_router(r, prefix=api_prefix)
    app.include_router(health.router)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest().decode(), media_type=CONTENT_TYPE_LATEST)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
                  for e in exc.errors()]
        return JSONResponse(status_code=422,
                            content={"detail": "Validation failed", "errors": errors})

    @app.exception_handler(PoolTimeoutError)
    @app.exception_handler(OperationalError)
    async def db_unavailable(_: Request, exc: Exception) -> JSONResponse:
        # Overload or DB outage: tell clients to retry instead of returning a 500.
        log.error("database_unavailable", extra={"error": type(exc).__name__})
        return JSONResponse(status_code=503, headers={"Retry-After": "2"},
                            content={"detail": "Service temporarily unavailable",
                                     "request_id": request_id_ctx.get()})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces to clients; log them with the request id instead.
        log.exception("unhandled_error")
        return JSONResponse(status_code=500, content={
            "detail": "Internal server error", "request_id": request_id_ctx.get()})

    log.info("startup", extra={"environment": settings.environment,
                               "version": settings.app_version})
    return app


app = create_app()
