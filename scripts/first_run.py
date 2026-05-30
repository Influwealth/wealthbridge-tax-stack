"""
First-run initialization script — creates an admin user.
Usage: ADMIN_USERNAME=admin ADMIN_PASSWORD=<strong-password> python scripts/first_run.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def main():
    if not ADMIN_PASSWORD:
        print("ERROR: Set ADMIN_PASSWORD environment variable before running.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if existing:
            print(f"User '{ADMIN_USERNAME}' already exists — skipping creation.")
            return
        user = User(
            username=ADMIN_USERNAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
        )
        db.add(user)
        db.commit()
        print(f"Admin user '{ADMIN_USERNAME}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
