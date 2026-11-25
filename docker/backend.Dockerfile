# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# DevSecOps360 backend — multi-stage build
#   stage 1 (builder): compile wheels into an isolated virtualenv
#   stage 2 (runtime): slim image, no compilers, non-root user, healthcheck
# Build context: apps/backend
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:${PYTHON_VERSION}-slim AS runtime
ARG APP_VERSION=1.0.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="devsecops360-backend" \
      org.opencontainers.image.description="DevSecOps360 FastAPI service" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/OWNER/devsecops360" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION} \
    PORT=8000

# Apply OS security patches, then create an unprivileged user (fixed UID for K8s runAsUser)
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app --chmod=0755 scripts/entrypoint.sh /usr/local/bin/entrypoint.sh

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
