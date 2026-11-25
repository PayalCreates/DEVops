# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# DevSecOps360 frontend — multi-stage build
#   stage 1 (build): install exact deps from lockfile (npm ci), test, build
#   stage 2 (runtime): unprivileged nginx (UID 101, port 8080) serving static files
# Build context: apps/frontend
# ---------------------------------------------------------------------------
ARG NODE_VERSION=22
ARG NGINX_VERSION=1.27

FROM node:${NODE_VERSION}-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Unit tests run inside the build so a broken UI can never produce an image.
RUN npm test && npm run build

FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine AS runtime
ARG APP_VERSION=1.0.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="devsecops360-frontend" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/OWNER/devsecops360" \
      org.opencontainers.image.licenses="MIT"

# Upstream for /api proxying; Compose: backend:8000, Kubernetes: backend service.
ENV BACKEND_UPSTREAM=backend:8000

USER root
RUN apk upgrade --no-cache && rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /src/dist /usr/share/nginx/html
USER 101

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/nginx-health"]
