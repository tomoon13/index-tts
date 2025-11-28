"""
User Model
==========

ORM model for users with email/password authentication.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model with email/password authentication"""

    __tablename__ = "users"

    # Primary key (auto-increment)
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="User ID",
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )

    # User profile
    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        comment="Optional username",
    )
    display_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Display name",
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether user is active",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email is verified",
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user is admin",
    )

    # Timestamps
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login timestamp",
    )

    # Usage tracking
    total_generations: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Total number of TTS generations",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
