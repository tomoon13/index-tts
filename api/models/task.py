"""
Task Model
==========

ORM model for TTS generation tasks.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base, TimestampMixin):
    """TTS Generation Task model"""

    __tablename__ = "tasks"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        comment="Task UUID (hex format)",
    )

    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who created this task",
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="tasks")

    # Status tracking
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current task status",
    )
    progress: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Progress percentage (0.0 to 1.0)",
    )
    message: Mapped[str] = mapped_column(
        String(255),
        default="",
        nullable=False,
        comment="Status message",
    )

    # Timestamps
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Completion timestamp",
    )

    # Input parameters (stored for reference)
    input_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Input text for TTS",
    )
    speech_length: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Target speech duration in ms",
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        default=0.8,
        nullable=False,
    )
    top_p: Mapped[float] = mapped_column(
        Float,
        default=0.8,
        nullable=False,
    )
    top_k: Mapped[int] = mapped_column(
        default=30,
        nullable=False,
    )
    emo_weight: Mapped[float] = mapped_column(
        Float,
        default=0.65,
        nullable=False,
    )
    emo_mode: Mapped[str] = mapped_column(
        String(20),
        default="speaker",
        nullable=False,
    )

    # Output
    output_file: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Path to generated audio file",
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if failed",
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status}, progress={self.progress})>"
