"""Locust load test for DevSecOps360.

Realistic mix: users log in once, then mostly read (list/filter/dashboard) and
sometimes write (create/update/delete). Each virtual user gets its own account.

Headless run (writes CSV + HTML report):
    locust -f load-testing/locustfile.py --host http://localhost:8080 \
        --headless -u 50 -r 5 -t 3m --csv load-testing/results/run --html load-testing/results/run.html

Pass/fail gates (checked at the end of the run, non-zero exit on breach):
    p95 latency < 300 ms  and  failure ratio < 1 %   (matches the SLOs)
"""

import os
import random
import uuid

from locust import HttpUser, between, events, tag, task

P95_BUDGET_MS = float(os.getenv("LOCUST_P95_MS", "300"))
MAX_FAIL_RATIO = float(os.getenv("LOCUST_MAX_FAIL_RATIO", "0.01"))
PRIORITIES = ["low", "medium", "high", "critical"]
STATUSES = ["todo", "in_progress", "done"]


class TaskUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.email = f"load-{uuid.uuid4().hex[:12]}@example.com"
        r = self.client.post("/api/v1/auth/register", name="/auth/register", json={
            "email": self.email, "password": "L0ad-Test-Pass", "full_name": "Load Tester"})
        if r.status_code != 201:
            r.failure(f"register failed: {r.status_code}")
            self.stop()
            return
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        self.task_ids: list[int] = []
        for i in range(3):
            self._create(f"seed task {i}")

    def _create(self, title: str) -> None:
        r = self.client.post("/api/v1/tasks", headers=self.headers, name="/tasks [POST]", json={
            "title": title, "priority": random.choice(PRIORITIES)})  # noqa: S311
        if r.status_code == 201:
            self.task_ids.append(r.json()["id"])

    @tag("read")
    @task(10)
    def list_tasks(self) -> None:
        self.client.get("/api/v1/tasks?size=20", headers=self.headers, name="/tasks [GET]")

    @tag("read")
    @task(4)
    def filter_tasks(self) -> None:
        st = random.choice(STATUSES)  # noqa: S311
        self.client.get(f"/api/v1/tasks?status={st}&sort=due_date&order=asc",
                        headers=self.headers, name="/tasks?status [GET]")

    @tag("read")
    @task(5)
    def dashboard(self) -> None:
        self.client.get("/api/v1/analytics/summary", headers=self.headers, name="/analytics/summary")

    @tag("write")
    @task(3)
    def create_task(self) -> None:
        self._create(f"load task {uuid.uuid4().hex[:6]}")

    @tag("write")
    @task(2)
    def update_task(self) -> None:
        if self.task_ids:
            tid = random.choice(self.task_ids)  # noqa: S311
            self.client.patch(f"/api/v1/tasks/{tid}", headers=self.headers, name="/tasks/{id} [PATCH]",
                              json={"status": random.choice(STATUSES)})  # noqa: S311

    @tag("write")
    @task(1)
    def delete_task(self) -> None:
        if len(self.task_ids) > 3:
            tid = self.task_ids.pop(0)
            self.client.delete(f"/api/v1/tasks/{tid}", headers=self.headers, name="/tasks/{id} [DELETE]")

    @task(1)
    def health(self) -> None:
        self.client.get("/health/ready", name="/health/ready")


@events.quitting.add_listener
def enforce_slo(environment, **_kwargs) -> None:
    stats = environment.stats.total
    if stats.num_requests == 0:
        return
    p95 = stats.get_response_time_percentile(0.95)
    fail_ratio = stats.fail_ratio
    verdict = p95 <= P95_BUDGET_MS and fail_ratio <= MAX_FAIL_RATIO
    print(f"\nSLO gate: p95={p95:.0f}ms (budget {P95_BUDGET_MS:.0f}) "
          f"fail_ratio={fail_ratio:.4f} (max {MAX_FAIL_RATIO}) -> {'PASS' if verdict else 'FAIL'}")
    if not verdict:
        environment.process_exit_code = 1
