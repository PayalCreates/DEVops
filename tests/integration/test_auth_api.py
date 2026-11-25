"""Integration tests: authentication, authorization and RBAC through the real API + DB."""

from app.models import Role


def test_register_returns_token_and_user_role(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "New@Example.com", "password": "Str0ngPassw0rd", "full_name": "New"})
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new@example.com"  # normalised
    assert body["user"]["role"] == "user"  # never self-assigned admin
    assert "hashed_password" not in body["user"]


def test_register_cannot_escalate_role(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "evil@example.com", "password": "Str0ngPassw0rd", "full_name": "Evil",
        "role": "admin"})
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "user"


def test_duplicate_email_conflict(client, register):
    register("dup@example.com")
    r = client.post("/api/v1/auth/register", json={
        "email": "DUP@example.com", "password": "Str0ngPassw0rd", "full_name": "Dup"})
    assert r.status_code == 409


def test_validation_error_shape(client):
    r = client.post("/api/v1/auth/register", json={"email": "x", "password": "a",
                                                    "full_name": ""})
    assert r.status_code == 422
    fields = {e["field"] for e in r.json()["errors"]}
    assert {"email", "password", "full_name"} <= fields


def test_login_success_and_me(client, register):
    register("login@example.com")
    r = client.post("/api/v1/auth/login",
                    json={"email": "login@example.com", "password": "Str0ngPassw0rd"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "login@example.com"


def test_login_wrong_password_and_unknown_user_same_error(client, register):
    register("victim@example.com")
    a = client.post("/api/v1/auth/login", json={"email": "victim@example.com",
                                                "password": "WrongPass1"})
    b = client.post("/api/v1/auth/login", json={"email": "ghost@example.com",
                                                "password": "WrongPass1"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()  # no user enumeration


def test_login_rate_limited(client, register, monkeypatch):
    from app.api.routes import auth

    register("brute@example.com")
    monkeypatch.setattr(auth.login_limiter, "limit", 3)
    codes = [client.post("/api/v1/auth/login", json={
        "email": "brute@example.com", "password": "Nope12345"}).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_protected_endpoints_require_token(client):
    assert client.get("/api/v1/tasks").status_code == 401
    assert client.get("/api/v1/auth/me",
                      headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_deactivated_user_rejected(client, auth_headers, make_admin):
    user_h = auth_headers("inactive@example.com")
    admin_h = make_admin()
    uid = client.get("/api/v1/auth/me", headers=user_h).json()["id"]
    r = client.patch(f"/api/v1/users/{uid}/active?active=false", headers=admin_h)
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=user_h).status_code == 401


def test_rbac_user_cannot_list_users(client, auth_headers):
    assert client.get("/api/v1/users", headers=auth_headers()).status_code == 403


def test_rbac_manager_can_list_but_not_change_roles(client, make_admin, auth_headers):
    mgr = make_admin("mgr@example.com", role=Role.MANAGER)
    auth_headers("someone@example.com")
    users = client.get("/api/v1/users", headers=mgr)
    assert users.status_code == 200 and len(users.json()) == 2
    target = users.json()[-1]["id"]
    r = client.patch(f"/api/v1/users/{target}/role", json={"role": "admin"}, headers=mgr)
    assert r.status_code == 403


def test_admin_can_promote_and_cannot_demote_self(client, make_admin, auth_headers):
    admin_h = make_admin()
    auth_headers("promote@example.com")
    users = client.get("/api/v1/users", headers=admin_h).json()
    me = next(u for u in users if u["email"] == "admin@example.com")
    other = next(u for u in users if u["email"] == "promote@example.com")
    r = client.patch(f"/api/v1/users/{other['id']}/role", json={"role": "manager"},
                     headers=admin_h)
    assert r.status_code == 200 and r.json()["role"] == "manager"
    r = client.patch(f"/api/v1/users/{me['id']}/role", json={"role": "user"}, headers=admin_h)
    assert r.status_code == 400
