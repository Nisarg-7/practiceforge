import pytest
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog, AuditOutcome
from app.models.user import Role, User
from helpers import TEST_DOMAIN, audit_rows, bearer, client, make_user

ADMIN_USERS = "/api/v1/admin/users"
AUDIT_LOGS = "/api/v1/admin/audit-logs"
ME = "/api/v1/users/me"


@pytest.fixture(autouse=True)
def cleanup_test_users():
    """Delete the users (and their audit rows) that these tests create."""
    yield
    with SessionLocal() as session:
        test_user_ids = select(User.id).where(User.email.like(f"%{TEST_DOMAIN}"))
        session.execute(delete(AuditLog).where(AuditLog.user_id.in_(test_user_ids)))
        session.execute(delete(User).where(User.email.like(f"%{TEST_DOMAIN}")))
        session.commit()


# ---------- who may enter ----------

def test_admin_endpoints_require_login() -> None:
    for url in (ADMIN_USERS, AUDIT_LOGS):
        assert client.get(url).status_code == 401


def test_student_forbidden_and_denial_audited() -> None:
    student = make_user()
    response = client.get(ADMIN_USERS, headers=bearer(student.token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    actions = {(r.action, r.outcome) for r in audit_rows(student.id)}
    assert ("authz.denied", AuditOutcome.DENIED) in actions


def test_instructor_forbidden_on_admin_endpoints() -> None:
    instructor = make_user(Role.INSTRUCTOR)
    assert client.get(ADMIN_USERS, headers=bearer(instructor.token)).status_code == 403
    assert client.get(AUDIT_LOGS, headers=bearer(instructor.token)).status_code == 403


# ---------- listing users ----------

def test_admin_lists_users_without_secrets() -> None:
    admin = make_user(Role.ADMIN)
    response = client.get(ADMIN_USERS, params={"page_size": 100}, headers=bearer(admin.token))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert admin.email in {u["email"] for u in body["items"]}
    assert all("password_hash" not in u for u in body["items"])


def test_list_users_role_filter() -> None:
    admin = make_user(Role.ADMIN)
    make_user(Role.INSTRUCTOR)
    response = client.get(
        ADMIN_USERS, params={"role": "ADMIN", "page_size": 100}, headers=bearer(admin.token)
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert items and all(u["role"] == "ADMIN" for u in items)


def test_list_users_pagination_validation() -> None:
    admin = make_user(Role.ADMIN)
    headers = bearer(admin.token)
    one = client.get(ADMIN_USERS, params={"page_size": 1}, headers=headers)
    assert one.status_code == 200 and len(one.json()["items"]) == 1
    assert client.get(ADMIN_USERS, params={"page_size": 0}, headers=headers).status_code == 422
    assert client.get(ADMIN_USERS, params={"page_size": 101}, headers=headers).status_code == 422
    assert client.get(ADMIN_USERS, params={"page": 0}, headers=headers).status_code == 422


# ---------- changing roles ----------

def test_admin_changes_role_and_it_applies_immediately() -> None:
    admin = make_user(Role.ADMIN)
    student = make_user()
    response = client.patch(
        f"{ADMIN_USERS}/{student.id}/role",
        json={"role": "INSTRUCTOR"},
        headers=bearer(admin.token),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "INSTRUCTOR"
    # The student's OLD token now shows the new role, because the role is read from the DB.
    me = client.get(ME, headers=bearer(student.token))
    assert me.json()["role"] == "INSTRUCTOR"


def test_student_cannot_change_role() -> None:
    student = make_user()
    other = make_user()
    response = client.patch(
        f"{ADMIN_USERS}/{other.id}/role", json={"role": "ADMIN"}, headers=bearer(student.token)
    )
    assert response.status_code == 403
    assert client.get(ME, headers=bearer(other.token)).json()["role"] == "STUDENT"


def test_admin_cannot_change_own_role() -> None:
    admin = make_user(Role.ADMIN)
    response = client.patch(
        f"{ADMIN_USERS}/{admin.id}/role", json={"role": "STUDENT"}, headers=bearer(admin.token)
    )
    assert response.status_code == 400
    assert client.get(ME, headers=bearer(admin.token)).json()["role"] == "ADMIN"


def test_invalid_role_rejected() -> None:
    admin = make_user(Role.ADMIN)
    student = make_user()
    headers = bearer(admin.token)
    url = f"{ADMIN_USERS}/{student.id}/role"
    assert client.patch(url, json={"role": "SUPERUSER"}, headers=headers).status_code == 422
    assert (
        client.patch(url, json={"role": "ADMIN", "is_active": False}, headers=headers).status_code
        == 422
    )


def test_unknown_user_404() -> None:
    admin = make_user(Role.ADMIN)
    response = client.patch(
        f"{ADMIN_USERS}/00000000-0000-0000-0000-000000000000/role",
        json={"role": "INSTRUCTOR"},
        headers=bearer(admin.token),
    )
    assert response.status_code == 404


# ---------- audit log ----------

def test_role_change_is_audited() -> None:
    admin = make_user(Role.ADMIN)
    student = make_user()
    client.patch(
        f"{ADMIN_USERS}/{student.id}/role",
        json={"role": "INSTRUCTOR"},
        headers=bearer(admin.token),
    )
    actions = {(r.action, r.outcome) for r in audit_rows(admin.id)}
    assert ("admin.change_role", AuditOutcome.ALLOWED) in actions


def test_audit_log_filters() -> None:
    admin = make_user(Role.ADMIN)
    student = make_user()  # registering and logging in wrote audit rows for this student
    headers = bearer(admin.token)

    logins = client.get(
        AUDIT_LOGS, params={"user_id": student.id, "action": "auth.login"}, headers=headers
    )
    assert logins.status_code == 200
    items = logins.json()["items"]
    assert items and all(i["action"] == "auth.login" and i["user_id"] == student.id for i in items)

    future = client.get(
        AUDIT_LOGS,
        params={"user_id": student.id, "date_from": "2100-01-01T00:00:00Z"},
        headers=headers,
    )
    assert future.json()["total"] == 0

    denied_only = client.get(
        AUDIT_LOGS, params={"user_id": student.id, "outcome": "DENIED"}, headers=headers
    )
    assert denied_only.json()["total"] == 0