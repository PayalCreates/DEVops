"""Prometheus metrics: RED (Rate, Errors, Duration) + business metrics."""

from prometheus_client import Counter, Gauge, Histogram, Info

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.3, 0.5, 1.0, 2.5, 5.0),
)
HTTP_IN_PROGRESS = Gauge("http_requests_in_progress", "In-flight HTTP requests")
TASKS_CREATED = Counter("tasks_created_total", "Tasks created")
LOGIN_ATTEMPTS = Counter("auth_login_attempts_total", "Login attempts", ["result"])
APP_INFO = Info("app", "Application build information")
