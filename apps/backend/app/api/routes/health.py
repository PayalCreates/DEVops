"""Health endpoints used by Docker, Kubernetes probes and blue-green switching.

- /health/live  : process is up (liveness probe) — never touches dependencies
- /health/ready : can serve traffic (readiness probe) — checks the database
- /api/v1/version : which version/colour is answering (used by traffic-switch validation)
"""

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas import HealthOut

router = APIRouter(tags=["health"])
log = logging.getLogger(__name__)


def _base(status_: str) -> HealthOut:
    s = get_settings()
    return HealthOut(status=status_, version=s.app_version, color=s.app_color,
                     environment=s.environment)


@router.get("/health/live", response_model=HealthOut)
def live() -> HealthOut:
    return _base("ok")


@router.get("/health/ready", response_model=HealthOut)
def ready(response: Response, db: Session = Depends(get_db)) -> HealthOut:
    out = _base("ok")
    try:
        db.execute(text("SELECT 1"))
        out.database = "ok"
    except Exception as exc:  # noqa: BLE001 - any DB failure means not ready
        log.error("readiness_db_failed", extra={"error": str(exc)})
        out.status, out.database = "degraded", "unreachable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return out


@router.get("/api/v1/version", response_model=HealthOut)
def version() -> HealthOut:
    return _base("ok")
