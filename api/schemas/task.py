"""
Task Schemas
============

Pydantic schemas for task-related API operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatusEnum(str, Enum):
    """Task status enumeration for API"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskBase(BaseModel):
    """Base task schema"""
    input_text: str = Field(..., max_length=500)
    speech_length: int = Field(default=0, ge=0)
    temperature: float = Field(default=0.8, ge=0.1, le=2.0)
    top_p: float = Field(default=0.8, ge=0.0, le=1.0)
    top_k: int = Field(default=30, ge=0, le=100)
    emo_weight: float = Field(default=0.65, ge=0.0, le=1.0)
    emo_mode: str = Field(default="speaker")


class TaskCreate(TaskBase):
    """Schema for creating a new task"""
    pass


class TaskInfo(BaseModel):
    """Task information response schema"""
    task_id: str
    status: TaskStatusEnum
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str = ""
    created_at: datetime
    completed_at: Optional[datetime] = None
    output_file: Optional[str] = None
    error: Optional[str] = None
    queue_position: Optional[int] = None

    model_config = {"from_attributes": True}


class GenerateResponse(BaseModel):
    """Response model for generate endpoint"""
    task_id: str
    status: TaskStatusEnum
    message: str
