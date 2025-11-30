"""
Job Schemas
===========

Pydantic schemas for TTS job-related API operations.
Following REST best practices for long-running tasks.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field, ConfigDict

from api.schemas.base import BaseModel


class JobStatusEnum(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobLinks(BaseModel):
    """HATEOAS links for job resources"""
    self_link: str = Field(..., alias="self", description="URL to this job")
    audio: Optional[str] = Field(None, description="URL to download audio (when completed)")

    model_config = ConfigDict(populate_by_name=True)


class JobCreateResponse(BaseModel):
    """Response for POST /jobs (202 Accepted)"""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatusEnum = Field(default=JobStatusEnum.PENDING)
    message: str = Field(default="Job created successfully")
    created_at: datetime = Field(..., description="Job creation timestamp")
    links: JobLinks = Field(..., description="Related resource URLs")


class JobInfo(BaseModel):
    """Job information for GET /jobs/{id}"""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatusEnum
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress (0.0 to 1.0)")
    message: Optional[str] = Field(None, description="Status message")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    queue_position: Optional[int] = Field(None, description="Position in queue (if pending)")
    links: JobLinks = Field(..., description="Related resource URLs")


class JobListItem(BaseModel):
    """Job item for list response (simplified)"""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatusEnum
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    queue_position: Optional[int] = None
    links: JobLinks


class JobListResponse(BaseModel):
    """Paginated job list response for GET /jobs"""
    jobs: list[JobListItem]
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
