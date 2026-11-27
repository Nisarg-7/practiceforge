from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    burn_dummy_verification,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models.audit_log import AuditOutcome
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.audit import log_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _invalid_credentials() -> HTTPException:
    # Security: one identical message for "unknown email" and "wrong password",
    # so an attacker cannot discover which emails are registered.
    return HTTPException(
        status_code=401,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    """Create a new refresh token row and an access token. Commits the whole transaction."""
    raw, hashed = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashed,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=raw,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> User:
    # The role is never read from the request: the model default (STUDENT) always applies.
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(user)
    log_event(
        db,
        action="auth.register",
        outcome=AuditOutcome.ALLOWED,
        request=request,
        user_id=user.id,
        target_type="user",
        target_id=str(user.id),
    )
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email))

    if user is None:
        burn_dummy_verification(body.password)
        log_event(db, action="auth.login", outcome=AuditOutcome.DENIED, request=request)
        raise _invalid_credentials()

    password_ok = verify_password(body.password, user.password_hash)
    if not password_ok or not user.is_active:
        log_event(
            db,
            action="auth.login",
            outcome=AuditOutcome.DENIED,
            request=request,
            user_id=user.id,
        )
        raise _invalid_credentials()

    tokens = _issue_tokens(db, user)
    log_event(
        db,
        action="auth.login",
        outcome=AuditOutcome.ALLOWED,
        request=request,
        user_id=user.id,
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    now = datetime.now(timezone.utc)
    token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )

    if token is None:
        log_event(db, action="auth.refresh", outcome=AuditOutcome.DENIED, request=request)
        raise _invalid_refresh()

    if token.revoked_at is not None:
        # Security: a revoked token coming back means it was probably stolen.
        # Revoke every live token of this user, which forces a fresh login everywhere.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        log_event(
            db,
            action="auth.refresh_reuse_detected",
            outcome=AuditOutcome.DENIED,
            request=request,
            user_id=token.user_id,
        )
        raise _invalid_refresh()

    user = db.get(User, token.user_id)
    if token.expires_at <= now or user is None or not user.is_active:
        log_event(
            db,
            action="auth.refresh",
            outcome=AuditOutcome.DENIED,
            request=request,
            user_id=token.user_id,
        )
        raise _invalid_refresh()

    # Rotation: revoke the old token and issue the new one in a single transaction.
    token.revoked_at = now
    tokens = _issue_tokens(db, user)
    log_event(
        db,
        action="auth.refresh",
        outcome=AuditOutcome.ALLOWED,
        request=request,
        user_id=user.id,
    )
    return tokens


@router.post("/logout", status_code=204)
def logout(body: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    # Idempotent: logging out with an unknown or already revoked token is not an error,
    # and it reveals nothing about which tokens exist.
    if token is not None and token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()
        log_event(
            db,
            action="auth.logout",
            outcome=AuditOutcome.ALLOWED,
            request=request,
            user_id=token.user_id,
        )
    return Response(status_code=204)