"""
Tasks Routes
============

Task management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.models.task import TaskStatus
from api.schemas import TaskInfo, TaskStatusEnum
from api.services import TaskService

router = APIRouter(prefix="/v1/tts", tags=["TTS"])


@router.get("/tasks", response_model=List[TaskInfo])
async def list_tasks(
    status: Optional[TaskStatusEnum] = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """
    List all tasks

    Returns a list of all tasks, optionally filtered by status.
    """
    task_service = TaskService(session)

    # Convert enum if provided
    db_status = TaskStatus(status.value) if status else None

    tasks = await task_service.get_tasks(status=db_status, limit=limit)

    # Convert to response format
    result = []
    for task in tasks:
        queue_position = None
        if task.status == TaskStatus.PENDING:
            queue_position = await task_service.get_queue_position(task.id)

        result.append(TaskInfo(
            task_id=task.id,
            status=TaskStatusEnum(task.status.value),
            progress=task.progress,
            message=task.message,
            created_at=task.created_at,
            completed_at=task.completed_at,
            output_file=task.output_file,
            error=task.error,
            queue_position=queue_position,
        ))

    return result


@router.get("/status/{task_id}", response_model=TaskInfo)
async def get_task_status(
    task_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get task status

    Returns the current status, progress, and other information about a task.
    """
    task_service = TaskService(session)
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(404, "Task not found")

    queue_position = None
    if task.status == TaskStatus.PENDING:
        queue_position = await task_service.get_queue_position(task_id)

    return TaskInfo(
        task_id=task.id,
        status=TaskStatusEnum(task.status.value),
        progress=task.progress,
        message=task.message,
        created_at=task.created_at,
        completed_at=task.completed_at,
        output_file=task.output_file,
        error=task.error,
        queue_position=queue_position,
    )


@router.get("/download/{task_id}")
async def download_result(
    task_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Download generated audio

    Returns the generated audio file if the task is completed.
    """
    task_service = TaskService(session)
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(404, "Task not found")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(425, f"Task not completed yet (status: {task.status.value})")

    if not task.output_file:
        raise HTTPException(404, "Output file not found")

    import os
    if not os.path.exists(task.output_file):
        raise HTTPException(404, "Output file not found on disk")

    return FileResponse(
        task.output_file,
        media_type="audio/wav",
        filename=f"{task_id}.wav",
    )


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a task

    Removes a task and its output file from the system.
    """
    task_service = TaskService(session)

    success = await task_service.delete_task(task_id)
    if not success:
        raise HTTPException(404, "Task not found")

    return {"message": "Task deleted successfully"}
