import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditOutcome
from app.models.user import Role
from app.schemas.auth import UserOut


class RoleUpdate(BaseModel):
    # Security: only "role" is accepted, and it must be one of the three enum values.
    model_config = ConfigDict(extra="forbid")

    role: Role


class UserPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    outcome: AuditOutcome
    ip_address: str | None
    created_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int