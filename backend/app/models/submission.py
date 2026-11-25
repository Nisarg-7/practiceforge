import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SubmissionKind(str, enum.Enum):
    RUN = "RUN"  # visible tests only, does not count toward mastery
    SUBMIT = "SUBMIT"  # all tests


class SubmissionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED_INTERNAL = "FAILED_INTERNAL"


class Verdict(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT = "TIME_LIMIT"
    MEMORY_LIMIT = "MEMORY_LIMIT"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILE_ERROR = "COMPILE_ERROR"


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        # Security: bound the size of untrusted input at the database level too.
        CheckConstraint("char_length(code) <= 50000", name="code_length"),
        Index("ix_submissions_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(Text)
    kind: Mapped[SubmissionKind] = mapped_column(
        Enum(SubmissionKind, native_enum=False, length=20)
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, native_enum=False, length=20),
        default=SubmissionStatus.QUEUED,
        server_default=SubmissionStatus.QUEUED.name,
        index=True,
    )
    final_verdict: Mapped[Verdict | None] = mapped_column(
        Enum(Verdict, native_enum=False, length=20), nullable=True
    )
    # How many times the worker has tried this job (used for bounded retries in Phase 4).
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )