#!/usr/bin/env python
"""
Promote or create an admin user (admin panel bootstrap).

Usage (inside the backend container on staging, or the backend venv locally):

    python promote_admin.py <email>                        # promote an existing user
    python promote_admin.py <email> --create               # create the account too
    python promote_admin.py <email> --create --password X  # ... with a password
    python promote_admin.py <email> --revoke               # demote back to plain user

Examples:
    docker compose exec backend python promote_admin.py me@company.com
    docker compose exec backend python promote_admin.py client@acme.com --create --password 'S3cret!'
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import func, select  # noqa: E402

from app.core.security import get_password_hash  # noqa: E402
from app.db.base import AsyncSessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


async def count_other_active_admins(db, user: User) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.role == "admin",
            User.is_active.is_(True),
            User.id != user.id,
        )
    )
    return int(result.scalar() or 0)


async def run(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == args.email))
        user = result.scalar_one_or_none()

        if args.revoke:
            if user is None:
                print(f"ERROR: no user with email {args.email}")
                return 1
            if user.role != "admin":
                print(f"{args.email} is already a plain user - nothing to do")
                return 0
            if await count_other_active_admins(db, user) == 0:
                print("ERROR: this is the only active admin - promote someone else first")
                return 1
            user.role = "user"
            await db.commit()
            print(f"OK: {args.email} demoted to role=user")
            return 0

        if user is None:
            if not args.create:
                print(
                    f"ERROR: no user with email {args.email}\n"
                    f"Either register at /register first, or re-run with --create."
                )
                return 1
            password = args.password or getpass.getpass("Password for the new admin: ")
            if len(password) < 8:
                print("ERROR: password must be at least 8 characters")
                return 1
            user = User(
                email=args.email,
                password_hash=get_password_hash(password),
                name=args.name,
                role="admin",
            )
            db.add(user)
            await db.commit()
            print(f"OK: created admin {args.email}")
            return 0

        if user.role == "admin":
            print(f"{args.email} is already an admin - nothing to do")
            return 0
        user.role = "admin"
        await db.commit()
        print(f"OK: {args.email} promoted to role=admin")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote or create an admin user")
    parser.add_argument("email", help="email of the user to promote/create")
    parser.add_argument("--create", action="store_true", help="create the account if missing")
    parser.add_argument("--password", help="password for --create (prompts if omitted)")
    parser.add_argument("--name", help="display name for --create")
    parser.add_argument("--revoke", action="store_true", help="demote the user to role=user")
    args = parser.parse_args()

    if args.create and args.revoke:
        parser.error("--create and --revoke are mutually exclusive")

    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
