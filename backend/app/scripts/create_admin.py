"""Bootstrap the first Admin from the command line.

Usage (from backend/, venv active):
    python -m app.scripts.create_admin you@example.com

If the email exists, that user is promoted. Otherwise a new Admin is created and
the password is typed at a hidden prompt (never passed as an argument, so it does
not end up in shell history).
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog, AuditOutcome
from app.models.user import Role, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an Admin user")
    parser.add_argument("email")
    email = parser.parse_args().email.strip().lower()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            password = getpass.getpass("Password for the new admin (min 8 chars): ")
            if len(password) < 8 or len(password) > 128:
                sys.exit("Password must be 8-128 characters.")
            if password != getpass.getpass("Repeat password: "):
                sys.exit("Passwords do not match.")
            user = User(email=email, password_hash=hash_password(password), role=Role.ADMIN)
            db.add(user)
            message = f"Created admin {email}"
        else:
            user.role = Role.ADMIN
            user.is_active = True
            message = f"Promoted {email} to ADMIN"

        db.flush()  # assigns the id
        db.add(
            AuditLog(
                user_id=user.id,
                action="cli.bootstrap_admin",
                target_type="user",
                target_id=str(user.id),
                outcome=AuditOutcome.ALLOWED,
            )
        )
        db.commit()
    print(message)


if __name__ == "__main__":
    main()