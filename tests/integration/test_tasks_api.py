"""Integration tests: task CRUD, ownership isolation, filtering, analytics."""

from datetime import date, timedelta

from app.models import Role


def _create(client, h, **kw):
    body = {"title": "Task", **kw}
    r = client.post("/api/v1/tasks", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_crud_lifecycle(client, auth_headers):
    h = auth_headers()
    t = _create(client, h, title="Write tests", priority="high",
                due_date=str(date.today() + timedelta(days=2)))
    assert t["status"] == "todo" and t["completed_at"] is None

    r = client.patch(f"/api/v1/tasks/{t['id']}", json={"status": "done"}, headers=h)
    assert r.status_code == 200 and r.json()["completed_at"] is not None

    r = client.patch(f"/api/v1/tasks/{t['id']}", json={"status": "in_progress"}, headers=h)
    assert r.json()["completed_at"] is None  # reopening clears completion

    assert client.get(f"/api/v1/tasks/{t['id']}", headers=h).status_code == 200
    assert client.delete(f"/api/v1/tasks/{t['id']}", headers=h).status_code == 204
    assert client.get(f"/api/v1/tasks/{t['id']}", headers=h).status_code == 404


def test_users_cannot_see_or_modify_each_others_tasks(client, auth_headers):
    alice, bob = auth_headers("alice@example.com"), auth_headers("bob@example.com")
    t = _create(client, alice, title="Alice's secret")
    assert client.get(f"/api/v1/tasks/{t['id']}", headers=bob).status_code == 404
    assert client.patch(f"/api/v1/tasks/{t['id']}", json={"title": "pwned"},
                        headers=bob).status_code == 404
    assert client.delete(f"/api/v1/tasks/{t['id']}", headers=bob).status_code == 404
    assert client.get("/api/v1/tasks", headers=bob).json()["total"] == 0


def test_manager_can_view_all_tasks(client, auth_headers, make_admin):
    alice = auth_headers("alice@example.com")
    _create(client, alice, title="A1")
    mgr = make_admin("mgr@example.com", role=Role.MANAGER)
    assert client.get("/api/v1/tasks", headers=mgr).json()["total"] == 0
    assert client.get("/api/v1/tasks?all_users=true", headers=mgr).json()["total"] == 1


def test_regular_user_all_users_flag_is_ignored(client, auth_headers):
    a, b = auth_headers("a@example.com"), auth_headers("b@example.com")
    _create(client, a, title="mine")
    assert client.get("/api/v1/tasks?all_users=true", headers=b).json()["total"] == 0


def test_filter_search_sort_paginate(client, auth_headers):
    h = auth_headers()
    for i, (st, pr) in enumerate([("todo", "low"), ("done", "high"), ("todo", "high"),
                                  ("in_progress", "critical")]):
        _create(client, h, title=f"Item {i} deploy" if i % 2 else f"Item {i}",
                status=st, priority=pr)
    j = client.get("/api/v1/tasks?status=todo", headers=h).json()
    assert j["total"] == 2
    j = client.get("/api/v1/tasks?priority=high&status=todo", headers=h).json()
    assert j["total"] == 1
    j = client.get("/api/v1/tasks?q=DEPLOY", headers=h).json()
    assert j["total"] == 2
    j = client.get("/api/v1/tasks?sort=title&order=asc&size=2&page=2", headers=h).json()
    assert [t["title"] for t in j["items"]] == ["Item 2", "Item 3 deploy"]
    assert client.get("/api/v1/tasks?sort=password", headers=h).status_code == 422
    assert client.get("/api/v1/tasks?size=1000", headers=h).status_code == 422


def test_invalid_task_payloads(client, auth_headers):
    h = auth_headers()
    assert client.post("/api/v1/tasks", json={"title": ""}, headers=h).status_code == 422
    assert client.post("/api/v1/tasks", json={"title": "x", "priority": "urgent"},
                       headers=h).status_code == 422
    t = _create(client, h)
    assert client.patch(f"/api/v1/tasks/{t['id']}", json={"status": None},
                        headers=h).status_code == 422
    assert client.patch(f"/api/v1/tasks/{t['id']}", json={"title": "   "},
                        headers=h).status_code == 422


def test_analytics_summary(client, auth_headers):
    h = auth_headers()
    today = date.today()
    _create(client, h, status="done", priority="high")
    _create(client, h, status="todo", due_date=str(today - timedelta(days=1)))  # overdue
    _create(client, h, status="in_progress", due_date=str(today + timedelta(days=3)))
    _create(client, h, status="done", due_date=str(today - timedelta(days=5)))  # done: not overdue
    a = client.get("/api/v1/analytics/summary", headers=h).json()
    assert a["total"] == 4
    assert a["by_status"] == {"todo": 1, "in_progress": 1, "done": 2}
    assert a["overdue"] == 1
    assert a["due_this_week"] == 1
    assert a["completion_rate"] == 50.0
    assert len(a["completed_last_7_days"]) == 7
    assert a["completed_last_7_days"][-1] == {"date": today.isoformat(), "count": 2}
