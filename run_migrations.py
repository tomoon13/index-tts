#!/usr/bin/env python3
"""
Database Migration Runner
==========================

Manually run database migrations.

Usage:
    uv run python run_migrations.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database import async_session_maker, run_migrations


async def main():
    """Run all pending migrations"""
    print("=" * 60)
    print("Database Migration Runner")
    print("=" * 60)

    try:
        async with async_session_maker() as session:
            await run_migrations(session)

        print("\n" + "=" * 60)
        print("[OK] All migrations completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
