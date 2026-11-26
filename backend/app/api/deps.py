from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

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