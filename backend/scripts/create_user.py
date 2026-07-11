import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.user import User


async def create_user(email: str, password: str, display_name: str) -> None:
    async with async_session_factory() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"User {email} already exists.")
            return
        user = User(email=email, hashed_password=hash_password(password), display_name=display_name)
        session.add(user)
        await session.commit()
        print(f"Created user {email}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the initial Quest for Health account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument(
        "--password-stdin", action="store_true", help="Read password from stdin instead of prompting"
    )
    args = parser.parse_args()

    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Confirm password: "):
            raise SystemExit("Passwords do not match.")

    asyncio.run(create_user(args.email, password, args.display_name))


if __name__ == "__main__":
    main()
