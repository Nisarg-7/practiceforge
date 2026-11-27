from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """A DB session that is always rolled back, so tests leave no data behind."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()