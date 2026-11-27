import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import Role, User

client = TestClient(app)

TEST_DOMAIN = "@pytest.example.com"
PASSWORD = "Correct-horse-9"


@dataclass
class Account:
    id: str
    email: str
    token: str  # access token


def new_email() -> str:
    return f"{uuid.uuid4().hex[:12]}{TEST_DOMAIN}"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_user(role: Role = Role.STUDENT) -> Account:
    """Register a user, set the role directly in the DB (as the bootstrap script would), log in."""
    email = new_email()
    registered = client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD}
    )
    assert registered.status_code == 201
    user_id = registered.json()["id"]

    if role != Role.STUDENT:
        with SessionLocal() as session:
            session.execute(
                update(User).where(User.id == uuid.UUID(user_id)).values(role=role)
            )
            session.commit()

    logged_in = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert logged_in.status_code == 200
    return Account(id=user_id, email=email, token=logged_in.json()["access_token"])


def audit_rows(user_id: str) -> list[AuditLog]:
    with SessionLocal() as session:
        return list(
            session.scalars(select(AuditLog).where(AuditLog.user_id == uuid.UUID(user_id)))
        )