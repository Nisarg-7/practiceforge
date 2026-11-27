import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProblemTestCase(Base):
    """Named ProblemTestCase (not TestCase) so pytest never mistakes it for a test class."""

    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("problem_id", "position", name="uq_test_cases_problem_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    input_data: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)
    # Security: hidden tests are never sent to Students (enforced in the API).
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    position: Mapped[int] = mapped_column(Integer)