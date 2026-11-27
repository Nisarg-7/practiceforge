from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.audit_log import AuditOutcome
from app.models.user import Role, User
from app.services.audit import log_event

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authentication: turn the Bearer token into a User, or reply 401."""
    if credentials is None:
        raise _unauthorized()
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _unauthorized()
    user = db.get(User, user_id)
    # Security: a deactivated or deleted user is locked out even if the token is still valid.
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


def require_role(*allowed: Role):
    """Authorization: build a dependency that only lets the listed roles through."""

    def checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.role not in allowed:
            # Security: every denied access is written to the audit log.
            log_event(
                db,
                action="authz.denied",
                outcome=AuditOutcome.DENIED,
                request=request,
                user_id=current_user.id,
                target_type="endpoint",
                target_id=request.url.path[:100],
            )
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return checker


require_admin = require_role(Role.ADMIN)
require_instructor_or_admin = require_role(Role.INSTRUCTOR, Role.ADMIN)