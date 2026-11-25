import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Difficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Problem(Base):
    __tablename__ = "problems"
    # Security/stability: the database itself rejects absurd limits, even if the API has a bug.
    __table_args__ = (
        CheckConstraint("time_limit_ms BETWEEN 100 AND 10000", name="time_limit"),
        CheckConstraint("memory_limit_mb BETWEEN 64 AND 512", name="memory_limit"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # RESTRICT: a user who authored problems cannot be deleted by accident.
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    statement_md: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, native_enum=False, length=20), index=True
    )
    time_limit_ms: Mapped[int] = mapped_column(
        Integer, default=2000, server_default="2000"
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        Integer, default=128, server_default="128"
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )