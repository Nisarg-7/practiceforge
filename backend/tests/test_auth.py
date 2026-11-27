import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog, AuditOutcome
from app.models.user import User

client = TestClient(app)

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/users/me"

TEST_DOMAIN = "@pytest.example.com"
PASSWORD = "Correct-horse-9"


def new_email() -> str:
    return f"{uuid.uuid4().hex[:12]}{TEST_DOMAIN}"


def register(email: str | None = None, password: str = PASSWORD):
    return client.post(REGISTER, json={"email": email or new_email(), "password": password})


def login(email: str, password: str = PASSWORD):
    return client.post(LOGIN, json={"email": email, "password": password})


def register_and_login() -> tuple[str, dict]:
    email = new_email()
    assert register(email).status_code == 201
    response = login(email)
    assert response.status_code == 200
    return email, response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def audit_rows(user_id: str) -> list[AuditLog]:
    with SessionLocal() as session:
        return list(
            session.scalars(select(AuditLog).where(AuditLog.user_id == uuid.UUID(user_id)))
        )


def make_token(secret: str, expires_in: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


@pytest.fixture(autouse=True)
def cleanup_test_users():
    """Delete the users (and their audit rows) that these tests create."""
    yield
    with SessionLocal() as session:
        test_user_ids = select(User.id).where(User.email.like(f"%{TEST_DOMAIN}"))
        session.execute(delete(AuditLog).where(AuditLog.user_id.in_(test_user_ids)))
        session.execute(delete(User).where(User.email.like(f"%{TEST_DOMAIN}")))
        session.commit()


# ---------- registration ----------

def test_register_creates_student_and_hides_hash() -> None:
    response = register()
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "STUDENT"
    assert "password" not in body and "password_hash" not in body


def test_register_cannot_choose_role() -> None:
    response = client.post(
        REGISTER, json={"email": new_email(), "password": PASSWORD, "role": "ADMIN"}
    )
    assert response.status_code == 422


def test_register_duplicate_email_conflict() -> None:
    email = new_email()
    assert register(email).status_code == 201
    response = register(email)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_register_short_password_rejected() -> None:
    assert register(password="short1").status_code == 422


def test_password_is_stored_hashed() -> None:
    email = new_email()
    register(email)
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2")


# ---------- login ----------

def test_login_success_and_me() -> None:
    email, tokens = register_and_login()
    assert tokens["token_type"] == "bearer"
    me = client.get(ME, headers=bearer(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "STUDENT"
    actions = {(r.action, r.outcome) for r in audit_rows(me.json()["id"])}
    assert ("auth.login", AuditOutcome.ALLOWED) in actions


def test_login_wrong_password_is_generic_and_audited() -> None:
    email = new_email()
    user_id = register(email).json()["id"]
    response = login(email, "wrong-password-1")
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password"
    actions = {(r.action, r.outcome) for r in audit_rows(user_id)}
    assert ("auth.login", AuditOutcome.DENIED) in actions


def test_login_unknown_email_looks_identical_to_wrong_password() -> None:
    email = new_email()
    register(email)
    wrong_password = login(email, "wrong-password-1")
    unknown_email = login(new_email(), "wrong-password-1")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_inactive_user_rejected() -> None:
    email = new_email()
    register(email)
    with SessionLocal() as session:
        session.execute(update(User).where(User.email == email).values(is_active=False))
        session.commit()
    assert login(email).status_code == 401


# ---------- access token checks ----------

BAD_HEADERS = {
    "no_header": {},
    "garbage_token": bearer("not-a-jwt"),
    "wrong_secret": bearer(make_token("x" * 40, timedelta(minutes=5))),
    "expired": bearer(make_token(settings.jwt_secret_key, timedelta(minutes=-5))),
}


@pytest.mark.parametrize("headers", BAD_HEADERS.values(), ids=BAD_HEADERS.keys())
def test_me_rejects_bad_tokens(headers: dict[str, str]) -> None:
    response = client.get(ME, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


# ---------- refresh and logout ----------

def test_refresh_rotates_token() -> None:
    _, tokens = register_and_login()
    response = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert client.get(ME, headers=bearer(new_tokens["access_token"])).status_code == 200


def test_reused_refresh_token_revokes_everything() -> None:
    _, tokens = register_and_login()
    new_tokens = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]}).json()
    user_id = client.get(ME, headers=bearer(new_tokens["access_token"])).json()["id"]

    # Replaying the old (revoked) token is rejected...
    replay = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    # ...and the newest token is revoked too, because theft is suspected.
    after = client.post(REFRESH, json={"refresh_token": new_tokens["refresh_token"]})
    assert after.status_code == 401
    actions = {r.action for r in audit_rows(user_id)}
    assert "auth.refresh_reuse_detected" in actions


def test_logout_revokes_refresh_token() -> None:
    _, tokens = register_and_login()
    assert client.post(LOGOUT, json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_refresh_unknown_token_rejected() -> None:
    response = client.post(REFRESH, json={"refresh_token": "x" * 60})
    assert response.status_code == 401