"""
Health Routes
=============

Health check and status endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import get_tts_model, get_task_semaphore
from api.schemas import HealthResponse
from api.services import TaskService
from api.config import settings

router = APIRouter(tags=["General"])


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "IndexTTS2 API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@router.get("/health", response_model=HealthResponse)
async def health(
    session: AsyncSession = Depends(get_session),
    tts_model=Depends(get_tts_model),
):
    """Health check endpoint"""
    task_service = TaskService(session)

    active_tasks = await task_service.get_processing_count()
    queue_length = await task_service.get_pending_count()

    # Check database connection
    db_connected = True
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
    except Exception:
        db_connected = False

    return HealthResponse(
        status="healthy" if tts_model else "unhealthy",
        model_loaded=tts_model is not None,
        active_tasks=active_tasks,
        queue_length=queue_length,
        max_workers=settings.MAX_CONCURRENT_TASKS,
        database_connected=db_connected,
    )
