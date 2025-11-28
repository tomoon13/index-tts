"""
Task Service
============

Business logic for task management with database persistence.
"""

import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.task import Task, TaskStatus


class TaskService:
    """Service for managing TTS tasks"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(
        self,
        task_id: str,
        input_text: str,
        speech_length: int = 0,
        temperature: float = 0.8,
        top_p: float = 0.8,
        top_k: int = 30,
        emo_weight: float = 0.65,
        emo_mode: str = "speaker",
    ) -> Task:
        """Create a new task"""
        task = Task(
            id=task_id,
            status=TaskStatus.PENDING,
            progress=0.0,
            message="Task queued",
            input_text=input_text,
            speech_length=speech_length,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            emo_weight=emo_weight,
            emo_mode=emo_mode,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        result = await self.session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """Get tasks with optional filtering"""
        query = select(Task).order_by(Task.created_at.desc())

        if status:
            query = query.where(Task.status == status)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: float = None,
        message: str = None,
        output_file: str = None,
        error: str = None,
    ) -> Optional[Task]:
        """Update task status"""
        task = await self.get_task(task_id)
        if not task:
            return None

        task.status = status

        if progress is not None:
            task.progress = progress
        if message is not None:
            task.message = message
        if output_file is not None:
            task.output_file = output_file
        if error is not None:
            task.error = error

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()

        await self.session.flush()
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task and its output file"""
        task = await self.get_task(task_id)
        if not task:
            return False

        # Delete output file if exists
        if task.output_file and os.path.exists(task.output_file):
            try:
                os.remove(task.output_file)
            except Exception as e:
                print(f"Failed to delete file: {e}")

        await self.session.delete(task)
        return True

    async def get_pending_count(self) -> int:
        """Get count of pending tasks"""
        result = await self.session.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.PENDING)
        )
        return result.scalar() or 0

    async def get_processing_count(self) -> int:
        """Get count of processing tasks"""
        result = await self.session.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.PROCESSING)
        )
        return result.scalar() or 0

    async def get_queue_position(self, task_id: str) -> Optional[int]:
        """Get the queue position of a pending task"""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return None

        result = await self.session.execute(
            select(func.count(Task.id)).where(
                Task.status == TaskStatus.PENDING,
                Task.created_at <= task.created_at,
            )
        )
        count = result.scalar() or 0
        return count - 1  # 0-indexed position

    async def cleanup_old_tasks(self, retention_seconds: int) -> int:
        """Clean up tasks older than retention period"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(seconds=retention_seconds)

        # Get old tasks
        result = await self.session.execute(
            select(Task).where(Task.created_at < cutoff)
        )
        old_tasks = list(result.scalars().all())

        deleted_count = 0
        for task in old_tasks:
            # Delete output file
            if task.output_file and os.path.exists(task.output_file):
                try:
                    os.remove(task.output_file)
                except Exception:
                    pass

            await self.session.delete(task)
            deleted_count += 1

        return deleted_count
