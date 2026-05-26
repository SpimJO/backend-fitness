#!/usr/bin/env python3
"""Create all tables and seed achievements + reward shop on PostgreSQL (Supabase)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.exc import OperationalError


def main() -> None:
    try:
        from app import create_app, db
    except OperationalError as exc:
        _print_connection_help(exc)
        sys.exit(1)

    try:
        app = create_app()
    except OperationalError as exc:
        _print_connection_help(exc)
        sys.exit(1)

    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
        except OperationalError as exc:
            _print_connection_help(exc)
            sys.exit(1)

        print("Connected to database (pooler/direct).")

        from app.models.rewards import RewardItem
        from app.models.social import Achievement

        ach = Achievement.query.count()
        items = RewardItem.query.count()
        print(f"Achievements in DB: {ach}")
        print(f"Reward shop items: {items}")
        print("Done — tables and seed data are ready.")


def _print_connection_help(exc: Exception) -> None:
    print("\n[init_db] Database connection failed:\n", exc)
    print(
        """
Fix (Windows / local PC):
  1. Supabase → Connect → Session pooler → copy the FULL URI
  2. Put it in backend/.env as DATABASE_URL
  3. Use pooler host like aws-1-ap-southeast-1.pooler.supabase.com
     (NOT db.xxxxx.supabase.co — that is IPv6-only and often fails locally)

Or skip Python: run backend/scripts/supabase_init.sql in Supabase SQL Editor.

Render: paste the same Session pooler DATABASE_URL in Environment variables.
"""
    )


if __name__ == "__main__":
    main()
