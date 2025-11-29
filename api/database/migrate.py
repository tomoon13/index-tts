"""
Database Migration Utilities
=============================

Handle database schema migrations for SQLite.
"""

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession


async def migrate_add_user_id_to_tasks(session: AsyncSession) -> bool:
    """
    Add user_id column to tasks table if it doesn't exist.

    Returns True if migration was applied, False if already migrated.
    """
    # Check if user_id column exists
    result = await session.execute(text("PRAGMA table_info(tasks)"))
    columns = result.fetchall()
    column_names = [col[1] for col in columns]

    if "user_id" in column_names:
        return False  # Already migrated

    print("  Applying migration: add user_id to tasks table...")

    try:
        # For SQLite, we need to recreate the table to add NOT NULL column with FK
        # Step 1: Create new table with user_id
        await session.execute(text("""
            CREATE TABLE tasks_new (
                id VARCHAR(32) NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status VARCHAR(10) NOT NULL,
                progress FLOAT NOT NULL,
                message VARCHAR(255) NOT NULL,
                completed_at TIMESTAMP,
                input_text TEXT NOT NULL,
                speech_length INTEGER NOT NULL,
                temperature FLOAT NOT NULL,
                top_p FLOAT NOT NULL,
                top_k INTEGER NOT NULL,
                emo_weight FLOAT NOT NULL,
                emo_mode VARCHAR(20) NOT NULL,
                output_file VARCHAR(512),
                error TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))

        # Step 2: Check if there's existing data
        result = await session.execute(text("SELECT COUNT(*) FROM tasks"))
        task_count = result.scalar()

        if task_count > 0:
            # Copy existing data, assign all tasks to user_id=1 (admin)
            print(f"  Migrating {task_count} existing tasks to user_id=1 (admin)...")
            await session.execute(text("""
                INSERT INTO tasks_new (
                    id, user_id, status, progress, message, completed_at,
                    input_text, speech_length, temperature, top_p, top_k,
                    emo_weight, emo_mode, output_file, error,
                    created_at, updated_at
                )
                SELECT
                    id, 1 as user_id, status, progress, message, completed_at,
                    input_text, speech_length, temperature, top_p, top_k,
                    emo_weight, emo_mode, output_file, error,
                    created_at, updated_at
                FROM tasks
            """))

        # Step 3: Drop old table
        await session.execute(text("DROP TABLE tasks"))

        # Step 4: Rename new table
        await session.execute(text("ALTER TABLE tasks_new RENAME TO tasks"))

        # Step 5: Recreate indexes
        await session.execute(text("CREATE INDEX ix_tasks_status ON tasks(status)"))
        await session.execute(text("CREATE INDEX ix_tasks_user_id ON tasks(user_id)"))

        await session.commit()

        print(f"  [OK] Migration complete: user_id column added to tasks")
        return True

    except Exception as e:
        await session.rollback()
        print(f"  [ERROR] Migration failed: {e}")
        raise


async def run_migrations(session: AsyncSession) -> None:
    """
    Run all pending database migrations.

    This function checks and applies necessary schema changes.
    """
    print("\nChecking for pending migrations...")

    migrations_applied = []

    # Migration 1: Add user_id to tasks
    if await migrate_add_user_id_to_tasks(session):
        migrations_applied.append("add_user_id_to_tasks")

    if migrations_applied:
        print(f"[OK] Applied {len(migrations_applied)} migration(s): {', '.join(migrations_applied)}")
    else:
        print("[OK] No pending migrations")
