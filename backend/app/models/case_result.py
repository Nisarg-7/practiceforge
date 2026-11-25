import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.submission import Verdict


class CaseResult(Base):
    """One row per test case per submission (table: test_results)."""

    __tablename__ = "test_results"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "test_case_id", name="uq_test_results_submission_case"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), index=True
    )
    verdict: Mapped[Verdict] = mapped_column(
        Enum(Verdict, native_enum=False, length=20), index=True
    )
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)