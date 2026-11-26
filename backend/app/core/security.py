import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

# Security: Argon2id with library defaults (salted, slow, memory-hard).
_hasher = PasswordHasher()

# Security: when an email is unknown we still verify against this dummy hash, so the
# response time does not reveal whether an account exists (timing side channel).
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def burn_dummy_verification(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    # The role is deliberately NOT in the token: it is read from the DB on every request,
    # so a role change or deactivation takes effect immediately.
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID | None:
    """Return the user id, or None if the token is invalid, expired or the wrong type."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            # Security: pin the algorithm list, so a forged "alg" header is never trusted.
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
        if payload.get("type") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None


def generate_refresh_token() -> tuple[str, str]:
    """Return (raw_token_for_the_client, sha256_hash_for_the_database)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    # SHA-256 is enough here: the token is 384 bits of randomness, so it cannot be guessed,
    # and a fast hash lets us look it up by value.
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()