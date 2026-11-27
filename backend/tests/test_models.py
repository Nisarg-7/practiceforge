import uuid

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import Difficulty, Problem, ProblemTestCase, Role, User

EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "topics",
    "problems",
    "problem_topics",
    "test_cases",
    "submissions",
    "test_results",
    "audit_logs",
}


def make_user(email: str | None = None) -> User:
    return User(email=email or f"{uuid.uuid4()}@test.local", password_hash="not-a-real-hash")


def make_problem(author_id: uuid.UUID, time_limit_ms: int = 2000) -> Problem:
    return Problem(
        author_id=author_id,
        title="Two Sum",
        statement_md="Find two numbers.",
        difficulty=Difficulty.EASY,
        time_limit_ms=time_limit_ms,
        memory_limit_mb=128,
    )


def test_all_tables_exist() -> None:
    # Needs the migration applied: alembic upgrade head
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_new_user_defaults_to_student(db: Session) -> None:
    user = make_user()
    db.add(user)
    db.flush()
    assert user.role == Role.STUDENT
    assert user.is_active is True


def test_duplicate_email_rejected(db: Session) -> None:
    db.add(make_user("same@test.local"))
    db.add(make_user("same@test.local"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_invalid_time_limit_rejected(db: Session) -> None:
    user = make_user()
    db.add(user)
    db.flush()
    db.add(make_problem(user.id, time_limit_ms=5))
    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_test_position_rejected(db: Session) -> None:
    user = make_user()
    db.add(user)
    db.flush()
    problem = make_problem(user.id)
    db.add(problem)
    db.flush()
    db.add(ProblemTestCase(problem_id=problem.id, input_data="1", expected_output="1", position=1))
    db.add(ProblemTestCase(problem_id=problem.id, input_data="2", expected_output="2", position=1))
    with pytest.raises(IntegrityError):
        db.flush()