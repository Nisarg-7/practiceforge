import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditOutcome


def client_ip(request: Request) -> str | None:
    # Behind a reverse proxy this would come from a trusted X-Forwarded-For header instead.
    return request.client.host if request.client else None


def log_event(
    db: Session,
    *,
    action: str,
    outcome: AuditOutcome,
    request: Request,
    user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> None:
    """Write one audit row and commit it immediately.

    It commits on its own so the record survives even when the request then fails
    with an error (for example a denied login).
    """
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            ip_address=client_ip(request),
        )
    )
    db.commit()