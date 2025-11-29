"""
Tasks Routes
============

Task management endpoints.
"""

from typing import List, Optional
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import get_current_user
from api.models.task import TaskStatus
from api.models.user import User
from api.schemas import TaskInfo, TaskStatusEnum, TaskListResponse
from api.services import TaskService

router = APIRouter(prefix="/v1/tts", tags=["TTS"])


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    user: User = Depends(get_current_user),
    status: Optional[TaskStatusEnum] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    """
    List current user's tasks with pagination

    Returns a paginated list of tasks belonging to the authenticated user,
    optionally filtered by status.
    """
    task_service = TaskService(session)

    # Convert enum if provided
    db_status = TaskStatus(status.value) if status else None

    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count
    total = await task_service.count_tasks(user_id=user.id, status=db_status)

    # Get tasks for current page
    tasks = await task_service.get_tasks(
        user_id=user.id,
        status=db_status,
        limit=page_size,
        offset=offset
    )

    # Convert to response format
    task_list = []
    for task in tasks:
        queue_position = None
        if task.status == TaskStatus.PENDING:
            queue_position = await task_service.get_queue_position(task.id)

        task_list.append(TaskInfo(
            taskId=task.id,
            status=TaskStatusEnum(task.status.value),
            progress=task.progress,
            message=task.message,
            createdAt=task.created_at,
            completedAt=task.completed_at,
            outputFile=task.output_file,
            error=task.error,
            queuePosition=queue_position,
        ))

    # Calculate total pages
    total_pages = ceil(total / page_size) if total > 0 else 0

    return TaskListResponse(
        tasks=task_list,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages,
    )


@router.get("/status/{task_id}", response_model=TaskInfo)
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get task status

    Returns the current status, progress, and other information about a task.
    Only accessible by the task owner.
    """
    task_service = TaskService(session)
    task = await task_service.get_task(task_id, user_id=user.id)

    if not task:
        raise HTTPException(404, "Task not found")

    queue_position = None
    if task.status == TaskStatus.PENDING:
        queue_position = await task_service.get_queue_position(task_id)

    return TaskInfo(
        taskId=task.id,
        status=TaskStatusEnum(task.status.value),
        progress=task.progress,
        message=task.message,
        createdAt=task.created_at,
        completedAt=task.completed_at,
        outputFile=task.output_file,
        error=task.error,
        queuePosition=queue_position,
    )


@router.get("/download/{task_id}")
async def download_result(
    task_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Download generated audio

    Returns the generated audio file if the task is completed.
    Only accessible by the task owner.
    """
    task_service = TaskService(session)
    task = await task_service.get_task(task_id, user_id=user.id)

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
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a task

    Removes a task and its output file from the system.
    Only accessible by the task owner.
    """
    task_service = TaskService(session)

    # Check if task belongs to user
    task = await task_service.get_task(task_id, user_id=user.id)
    if not task:
        raise HTTPException(404, "Task not found")

    success = await task_service.delete_task(task_id)
    if not success:
        raise HTTPException(404, "Task not found")

    return {"message": "Task deleted successfully"}
