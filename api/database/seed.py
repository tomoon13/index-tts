"""
Database Seed
=============

Seed initial data for development and production.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.user import User
from api.services.auth_service import AuthService


async def seed_admin_user(session: AsyncSession) -> User:
    """
    Create default admin user if not exists.

    Default credentials:
    - Email: admin@example.com
    - Password: test123
    - Username: admin
    """
    # Check if admin user already exists
    result = await session.execute(
        select(User).where(User.email == "admin@example.com")
    )
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        print("✓ Admin user already exists (admin@example.com)")
        return existing_admin

    # Create admin user
    admin = User(
        email="admin@example.com",
        hashed_password=AuthService.hash_password("test123"),
        username="admin",
        display_name="Administrator",
        is_active=True,
        is_verified=True,
        is_admin=True,
    )

    session.add(admin)
    await session.flush()

    print("✓ Admin user created:")
    print("  Email: admin@example.com")
    print("  Password: test123")
    print("  Username: admin")

    return admin


async def seed_database(session: AsyncSession) -> None:
    """Seed all initial data"""
    print("\n" + "=" * 60)
    print("Seeding Database")
    print("=" * 60)

    # Seed admin user
    await seed_admin_user(session)

    # Commit all changes
    await session.commit()

    print("=" * 60)
    print("✓ Database seeding complete")
    print("=" * 60 + "\n")
