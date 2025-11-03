"""Utility script to initialize the database schema and seed an admin user.

Run once per environment, after configuring your .env, e.g.:
    python scripts/bootstrap.py --email admin@example.com --full-name "Site Admin"

You will be prompted for a password if --password is not supplied.
"""

from __future__ import annotations

import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import AdminUser, Base
from app.db.session import SessionLocal, database_engine


def create_tables() -> None:
    """Create all database tables defined on the metadata."""
    Base.metadata.create_all(bind=database_engine)


def ensure_admin_user(uname: str, password: str | None, name: str | None) -> tuple[AdminUser, bool]:
    """Create or update the admin user record matching the email.

    Returns the admin instance and a flag indicating whether it was newly created.
    """
    with SessionLocal() as session:
        admin = session.execute(select(AdminUser).where(AdminUser.user_name == uname)).scalar_one_or_none()

        if admin:
            if name:
                admin.full_name = name
            if password:
                admin.password_hash = hash_password(password)
            session.commit()
            session.refresh(admin)
            return admin, False

        if not password:
            raise ValueError("A password is required when creating a new admin user.")

        admin = AdminUser(
            user_name=uname,
            password_hash=hash_password(password),
            full_name=name,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin, True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Setup database tables and seed the admin user.")
    parser.add_argument("--uname", required=True, help="User Name for the admin account.")
    parser.add_argument(
        "--password",
        help="Password for the admin account (omit to receive an interactive prompt).",
    )
    parser.add_argument(
        "--full-name",
        default=None,
        help="Optional display name for the admin account.",
    )
    parser.add_argument(
        "--skip-tables",
        action="store_true",
        help="Skip creating tables (useful when they already exist).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Ensure settings are loaded so environment variables are validated early.
    settings = get_settings()
    print(f"Using database: {settings.database_url}")

    if not args.skip_tables:
        print("Creating database tables (no-op if already present)...")
        create_tables()
        print("Tables ensured.")
    else:
        print("Skipping table creation.")

    password = args.password
    if password is None:
        password = getpass("Admin password (leave blank to keep current if account exists): ").strip() or None

    try:
        admin, created = ensure_admin_user(args.uname, password, args.full_name)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    if created:
        print(f"Admin user created with email: {admin.user_name}")
    else:
        if password:
            print(f"Admin user {admin.user_name} updated (password refreshed).")
        elif args.full_name:
            print(f"Admin user {admin.user_name} updated (profile refreshed).")
        else:
            print(f"Admin user {admin.user_name} already exists. No changes applied.")

    print("Bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
