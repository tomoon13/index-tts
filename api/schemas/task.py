"""
Task Schemas
============

Pydantic schemas for task-related API operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TaskStatusEnum(str, Enum):
    """Task status enumeration for API"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskBase(BaseModel):
    """Base task schema"""
    inputText: str = Field(..., max_length=500, serialization_alias="inputText")
    speechLength: int = Field(default=0, ge=0, serialization_alias="speechLength")
    temperature: float = Field(default=0.8, ge=0.1, le=2.0)
    topP: float = Field(default=0.8, ge=0.0, le=1.0, serialization_alias="topP")
    topK: int = Field(default=30, ge=0, le=100, serialization_alias="topK")
    emoWeight: float = Field(default=0.65, ge=0.0, le=1.0, serialization_alias="emoWeight")
    emoMode: str = Field(default="speaker", serialization_alias="emoMode")

    model_config = ConfigDict(populate_by_name=True)


class TaskCreate(TaskBase):
    """Schema for creating a new task"""
    pass


class TaskInfo(BaseModel):
    """Task information response schema"""
    taskId: str = Field(..., serialization_alias="taskId")
    status: TaskStatusEnum
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str = ""
    createdAt: datetime = Field(..., serialization_alias="createdAt")
    completedAt: Optional[datetime] = Field(None, serialization_alias="completedAt")
    outputFile: Optional[str] = Field(None, serialization_alias="outputFile")
    error: Optional[str] = None
    queuePosition: Optional[int] = Field(None, serialization_alias="queuePosition")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class GenerateResponse(BaseModel):
    """Response model for generate endpoint"""
    taskId: str = Field(..., serialization_alias="taskId")
    status: TaskStatusEnum
    message: str

    model_config = ConfigDict(populate_by_name=True)


class TaskListResponse(BaseModel):
    """Paginated task list response"""
    tasks: list[TaskInfo]
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(..., ge=1, description="Current page number")
    pageSize: int = Field(..., ge=1, le=100, serialization_alias="pageSize", description="Number of items per page")
    totalPages: int = Field(..., ge=0, serialization_alias="totalPages", description="Total number of pages")

    model_config = ConfigDict(populate_by_name=True)
