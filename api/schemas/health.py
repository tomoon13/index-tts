"""
Health Schemas
==============

Pydantic schemas for health check endpoints.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for health endpoint"""
    status: str
    model_loaded: bool
    active_tasks: int
    queue_length: int
    max_workers: int
    database_connected: bool = True
