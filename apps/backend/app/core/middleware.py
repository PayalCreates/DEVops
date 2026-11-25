"""HTTP middleware: request IDs, access logging, metrics and security headers."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_ctx
from app.core.metrics import HTTP_IN_PROGRESS, HTTP_LATENCY, HTTP_REQUESTS

log = logging.getLogger("app.access")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}
# The API serves JSON only; Swagger UI pages need CDN assets so get a looser CSP.
API_CSP = "default-src 'none'; frame-ancestors 'none'"
DOCS_CSP = (
    "default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; frame-ancestors 'none'"
)


def _route_template(request: Request) -> str:
    """Use the route template (/tasks/{task_id}) to keep metric cardinality low."""
    if request.scope.get("route") is None:
        return "unmatched"
    # Rebuild the template from the concrete path + matched params. This is
    # independent of how routers are nested/prefixed internally.
    params = {str(v): k for k, v in request.scope.get("path_params", {}).items()}
    segments = request.url.path.split("/")
    return "/".join("{" + params[s] + "}" if s in params else s for s in segments)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        # Not reset afterwards on purpose: the context is per-request, and keeping it
        # lets the outer error handlers log the request id too.
        request_id_ctx.set(rid)
        start = time.perf_counter()
        HTTP_IN_PROGRESS.inc()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            elapsed = time.perf_counter() - start
            HTTP_IN_PROGRESS.dec()
            route = _route_template(request)
            if route not in ("/metrics",):
                HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
                HTTP_LATENCY.labels(request.method, route).observe(elapsed)
                if not route.startswith("/health"):
                    log.info(
                        "request",
                        extra={
                            "method": request.method,
                            "path": request.url.path,
                            "route": route,
                            "status": status,
                            "duration_ms": round(elapsed * 1000, 2),
                            "client": request.client.host if request.client else None,
                        },
                    )

        response.headers["X-Request-ID"] = rid
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        is_docs = request.url.path.startswith(("/docs", "/redoc"))
        response.headers.setdefault("Content-Security-Policy", DOCS_CSP if is_docs else API_CSP)
        return response
