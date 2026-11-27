import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog, AuditOutcome
from app.models.user import Role, User
from app.schemas.admin import AuditLogOut, AuditLogPage, RoleUpdate, UserPage
from app.schemas.auth import UserOut
from app.services.audit import log_event

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserPage)
def list_users(
    role: Role | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),  # capped, so nobody can request a million rows
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserPage:
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if role is not None:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    total = db.scalar(count_query) or 0
    users = db.scalars(
        query.order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return UserPage(
        items=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: uuid.UUID,
    body: RoleUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    if user_id == admin.id:
        # Safety: an admin cannot demote themselves, so the system never ends up admin-less.
        log_event(
            db,
            action="admin.change_role",
            outcome=AuditOutcome.DENIED,
            request=request,
            user_id=admin.id,
            target_type="user",
            target_id=str(user_id),
        )
        raise HTTPException(status_code=400, detail="Admins cannot change their own role")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = body.role
    db.commit()
    db.refresh(user)
    log_event(
        db,
        action="admin.change_role",
        outcome=AuditOutcome.ALLOWED,
        request=request,
        user_id=admin.id,
        target_type="user",
        target_id=str(user.id),
    )
    return user


@router.get("/audit-logs", response_model=AuditLogPage)
def list_audit_logs(
    user_id: uuid.UUID | None = None,
    action: str | None = Query(None, max_length=100),
    outcome: AuditOutcome | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)

    conditions = []
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if action is not None:
        conditions.append(AuditLog.action == action)
    if outcome is not None:
        conditions.append(AuditLog.outcome == outcome)
    if date_from is not None:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to is not None:
        conditions.append(AuditLog.created_at <= date_to)
    for condition in conditions:
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = db.scalar(count_query) or 0
    rows = db.scalars(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AuditLogPage(
        items=[AuditLogOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )